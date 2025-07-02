declare module 'gray-matter' {
  interface GrayMatterOption<I = any, O = any> {
    engines?: any
    language?: string
    delimiters?: string | string[]
    excerpt?: boolean | ((input: I, options: O) => string)
    excerpt_separator?: string
  }

  interface GrayMatterFile<I = any> {
    data: { [key: string]: any }
    content: string
    excerpt?: string
    orig: I
    language?: string
    matter?: string
    stringify?: (lang?: string) => string
  }

  function matter<I = any, O = any>(input: I, options?: GrayMatterOption<I, O>): GrayMatterFile<I>

  export = matter
}
