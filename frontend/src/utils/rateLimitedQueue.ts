/**
 * Rate-limited request queue to prevent 429 errors
 * Manages API requests to stay within rate limits
 */
export class RateLimitedQueue {
  private queue: Array<() => Promise<any>> = [];
  private processing = false;
  private requestsInWindow: number[] = [];
  
  constructor(
    private maxRequestsPerSecond: number = 8, // Stay under nginx limit of 10r/s
    private windowMs: number = 1000
  ) {}

  /**
   * Add a request to the queue
   */
  async add<T>(requestFn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          const result = await requestFn();
          resolve(result);
        } catch (error) {
          reject(error);
        }
      });
      
      if (!this.processing) {
        this.process();
      }
    });
  }

  /**
   * Process queued requests while respecting rate limits
   */
  private async process() {
    if (this.processing || this.queue.length === 0) {
      return;
    }

    this.processing = true;

    while (this.queue.length > 0) {
      // Clean up old requests outside the window
      const now = Date.now();
      this.requestsInWindow = this.requestsInWindow.filter(
        time => now - time < this.windowMs
      );

      // Check if we can make another request
      if (this.requestsInWindow.length < this.maxRequestsPerSecond) {
        const request = this.queue.shift();
        if (request) {
          this.requestsInWindow.push(now);
          
          // Execute request without waiting (allows parallel execution)
          request().catch(console.error);
        }
      } else {
        // Wait before checking again
        const oldestRequest = Math.min(...this.requestsInWindow);
        const waitTime = Math.max(0, this.windowMs - (now - oldestRequest) + 10);
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    }

    this.processing = false;
  }

  /**
   * Get queue statistics
   */
  getStats() {
    return {
      queueLength: this.queue.length,
      requestsInCurrentWindow: this.requestsInWindow.length,
      isProcessing: this.processing
    };
  }
}

// Singleton instance for the app
let apiQueueInstance: RateLimitedQueue | null = null;

export function getApiQueue(): RateLimitedQueue {
  if (!apiQueueInstance) {
    apiQueueInstance = new RateLimitedQueue();
  }
  return apiQueueInstance;
}