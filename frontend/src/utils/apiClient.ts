/**
 * API client with automatic retry and exponential backoff
 * Handles rate limiting (429) and other transient errors gracefully
 */

interface RetryOptions {
  maxRetries?: number;
  initialDelay?: number;
  maxDelay?: number;
  backoffFactor?: number;
  retryOn?: number[];
}

const DEFAULT_RETRY_OPTIONS: Required<RetryOptions> = {
  maxRetries: 3,
  initialDelay: 1000,      // Start with 1 second
  maxDelay: 10000,         // Max 10 seconds
  backoffFactor: 2,        // Double each time
  retryOn: [429, 502, 503, 504] // Rate limit and server errors
};

export class ApiClient {
  constructor(private baseUrl: string = '') {}

  /**
   * Fetch with automatic retry and exponential backoff
   */
  async fetchWithRetry(
    url: string, 
    options?: RequestInit, 
    retryOptions?: RetryOptions
  ): Promise<Response> {
    const config = { ...DEFAULT_RETRY_OPTIONS, ...retryOptions };
    let lastError: Error | null = null;
    
    for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
      try {
        const response = await fetch(`${this.baseUrl}${url}`, options);
        
        // Success or non-retryable error
        if (!config.retryOn.includes(response.status)) {
          return response;
        }
        
        // Rate limit hit - extract retry-after if available
        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After');
          const delay = retryAfter 
            ? parseInt(retryAfter) * 1000 
            : Math.min(config.initialDelay * Math.pow(config.backoffFactor, attempt), config.maxDelay);
          
          console.warn(`Rate limited. Retrying after ${delay}ms (attempt ${attempt + 1}/${config.maxRetries})`);
          
          if (attempt < config.maxRetries) {
            await this.delay(delay);
            continue;
          }
        }
        
        // Other retryable errors
        const delay = Math.min(
          config.initialDelay * Math.pow(config.backoffFactor, attempt), 
          config.maxDelay
        );
        
        console.warn(`Request failed with ${response.status}. Retrying after ${delay}ms`);
        
        if (attempt < config.maxRetries) {
          await this.delay(delay);
          continue;
        }
        
        // Max retries reached
        return response;
        
      } catch (error) {
        lastError = error as Error;
        
        // Network errors - always retry
        if (attempt < config.maxRetries) {
          const delay = Math.min(
            config.initialDelay * Math.pow(config.backoffFactor, attempt), 
            config.maxDelay
          );
          
          console.warn(`Network error. Retrying after ${delay}ms`, error);
          await this.delay(delay);
          continue;
        }
      }
    }
    
    throw lastError || new Error('Max retries reached');
  }

  /**
   * Submit a single evaluation
   */
  async submitEvaluation(code: string, options?: any): Promise<any> {
    const response = await this.fetchWithRetry('/api/eval', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, ...options })
    });

    if (!response.ok && response.status !== 429) {
      const error = await response.json();
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Submit multiple evaluations as a batch
   * Falls back to individual submissions if batch endpoint doesn't exist
   */
  async submitBatch(evaluations: Array<{ code: string; options?: any }>): Promise<any[]> {
    // First, try the batch endpoint
    try {
      const response = await this.fetchWithRetry('/api/eval-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ evaluations })
      }, {
        maxRetries: 0 // Don't retry the batch endpoint check
      });

      if (response.ok) {
        return response.json();
      }
      
      // If 404, fall back to individual submissions
      if (response.status !== 404) {
        const error = await response.json();
        throw new Error(error.error || `HTTP ${response.status}`);
      }
    } catch (error) {
      // Batch endpoint doesn't exist, continue with fallback
    }

    // Fallback: Submit individually with automatic retry/backoff
    console.log('Batch endpoint not available, submitting individually with rate limit protection');
    
    const results = [];
    for (const [index, evaluation] of evaluations.entries()) {
      try {
        // Small delay between submissions to be nice to the server
        if (index > 0) {
          await this.delay(100);
        }
        
        const result = await this.submitEvaluation(evaluation.code, evaluation.options);
        results.push(result);
      } catch (error) {
        results.push({ 
          error: error instanceof Error ? error.message : 'Submission failed',
          index 
        });
      }
    }
    
    return results;
  }

  /**
   * Check evaluation status
   */
  async checkStatus(evalId: string): Promise<any> {
    const response = await this.fetchWithRetry(`/api/eval-status/${evalId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch status: HTTP ${response.status}`);
    }
    
    return response.json();
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Export singleton instance
export const apiClient = new ApiClient(process.env.NEXT_PUBLIC_API_URL || '');