/**
 * Smart API client that combines proactive rate limiting with reactive backoff
 * 
 * Strategy:
 * 1. Proactively limit requests to stay under server limits
 * 2. If we still get 429, back off exponentially
 * 3. Dynamically adjust rate limit based on 429 responses
 */

interface QueuedRequest<T> {
  execute: () => Promise<Response>;
  resolve: (value: T) => void;
  reject: (error: any) => void;
  retries: number;
}

export class SmartApiClient {
  private queue: QueuedRequest<any>[] = [];
  private processing = false;
  private tokensAvailable: number;
  private lastRefill: number = Date.now();
  
  // Dynamic rate limiting
  private currentRateLimit: number;
  private readonly minRateLimit = 2;  // Minimum 2 requests per second
  private readonly maxRateLimit = 8;  // Maximum 8 requests per second
  
  // Backoff state
  private consecutiveRateLimits = 0;
  private backoffUntil = 0;

  constructor(
    private baseUrl: string = '',
    initialRateLimit: number = 6 // Start conservative
  ) {
    this.currentRateLimit = initialRateLimit;
    this.tokensAvailable = this.currentRateLimit;
  }

  /**
   * Make an API request with smart rate limiting
   */
  async fetch<T>(url: string, options?: RequestInit): Promise<T> {
    return new Promise((resolve, reject) => {
      const request: QueuedRequest<T> = {
        execute: () => fetch(`${this.baseUrl}${url}`, options),
        resolve,
        reject,
        retries: 0
      };

      this.queue.push(request);
      this.processQueue();
    });
  }

  /**
   * Process queued requests with token bucket algorithm
   */
  private async processQueue() {
    if (this.processing) return;
    this.processing = true;

    while (this.queue.length > 0) {
      // Check if we're in backoff period
      const now = Date.now();
      if (now < this.backoffUntil) {
        await this.delay(this.backoffUntil - now);
        continue;
      }

      // Refill tokens based on time passed
      this.refillTokens();

      // Wait for a token to be available
      if (this.tokensAvailable < 1) {
        const waitTime = (1000 / this.currentRateLimit) - (now - this.lastRefill);
        await this.delay(Math.max(10, waitTime));
        continue;
      }

      // Process next request
      const request = this.queue.shift()!;
      this.tokensAvailable--;

      try {
        const response = await request.execute();

        if (response.status === 429) {
          // Rate limited! Adjust our behavior
          this.handleRateLimit(request, response);
        } else {
          // Success! Maybe we can go faster
          this.handleSuccess();
          
          if (!response.ok) {
            request.reject(new Error(`HTTP ${response.status}: ${response.statusText}`));
          } else {
            const data = await response.json();
            request.resolve(data);
          }
        }
      } catch (error) {
        // Network error - retry with backoff
        if (request.retries < 3) {
          request.retries++;
          this.queue.unshift(request); // Put back at front
          await this.delay(Math.pow(2, request.retries) * 1000);
        } else {
          request.reject(error);
        }
      }
    }

    this.processing = false;
  }

  /**
   * Handle 429 rate limit response
   */
  private handleRateLimit<T>(request: QueuedRequest<T>, response: Response) {
    this.consecutiveRateLimits++;
    
    // Get retry-after header if available
    const retryAfter = response.headers.get('Retry-After');
    const backoffMs = retryAfter 
      ? parseInt(retryAfter) * 1000 
      : Math.min(Math.pow(2, this.consecutiveRateLimits) * 1000, 30000);

    console.warn(`Rate limited! Backing off for ${backoffMs}ms. Reducing rate limit.`);

    // Reduce our rate limit
    this.currentRateLimit = Math.max(
      this.minRateLimit,
      this.currentRateLimit * 0.7 // Reduce by 30%
    );
    
    // Set backoff period
    this.backoffUntil = Date.now() + backoffMs;
    
    // Requeue the request
    if (request.retries < 3) {
      request.retries++;
      this.queue.unshift(request);
    } else {
      request.reject(new Error('Rate limited after 3 retries'));
    }
  }

  /**
   * Handle successful request
   */
  private handleSuccess() {
    this.consecutiveRateLimits = 0;
    
    // Slowly increase rate limit on success
    if (Math.random() < 0.1) { // 10% chance to increase
      this.currentRateLimit = Math.min(
        this.maxRateLimit,
        this.currentRateLimit * 1.1 // Increase by 10%
      );
    }
  }

  /**
   * Refill tokens based on time passed
   */
  private refillTokens() {
    const now = Date.now();
    const timePassed = now - this.lastRefill;
    const tokensToAdd = (timePassed / 1000) * this.currentRateLimit;
    
    this.tokensAvailable = Math.min(
      this.currentRateLimit, // Token bucket size
      this.tokensAvailable + tokensToAdd
    );
    
    this.lastRefill = now;
  }

  /**
   * Convenience methods for common operations
   */
  async submitEvaluation(code: string, options?: any): Promise<any> {
    return this.fetch('/api/eval', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, ...options })
    });
  }

  async submitBatch(evaluations: Array<{ code: string; options?: any }>): Promise<any[]> {
    // Try batch endpoint first
    try {
      return await this.fetch('/api/eval-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ evaluations })
      });
    } catch (error) {
      // Fallback to individual submissions
      console.log('Batch endpoint not available, submitting individually');
      
      const results = [];
      for (const eval of evaluations) {
        try {
          const result = await this.submitEvaluation(eval.code, eval.options);
          results.push(result);
        } catch (error) {
          results.push({ error: error instanceof Error ? error.message : 'Failed' });
        }
      }
      return results;
    }
  }

  async checkStatus(evalId: string): Promise<any> {
    return this.fetch(`/api/eval-status/${evalId}`);
  }

  /**
   * Get current client statistics
   */
  getStats() {
    return {
      queueLength: this.queue.length,
      currentRateLimit: this.currentRateLimit.toFixed(1),
      tokensAvailable: this.tokensAvailable.toFixed(1),
      isBackingOff: Date.now() < this.backoffUntil,
      backoffRemaining: Math.max(0, this.backoffUntil - Date.now())
    };
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Export singleton
export const smartApi = new SmartApiClient(process.env.NEXT_PUBLIC_API_URL || '');