declare module 'remark-wiki-link' {
  import { Plugin } from 'unified'

  interface RemarkWikiLinkOptions {
    pageResolver?: (name: string) => string[]
    hrefTemplate?: (permalink: string) => string
    wikiLinkClassName?: string
    newClassName?: string
  }

  const remarkWikiLink: Plugin<[RemarkWikiLinkOptions?]>
  export default remarkWikiLink
}
