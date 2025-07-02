export interface SlideMetadata {
  id: string
  title: string
  file: string
  duration: number
  tags: string[]
}

export interface SlidePresentation {
  title: string
  description: string
  author: string
  date: string
  theme: string
  slides: SlideMetadata[]
  totalDuration: number
  config: RevealConfig
}

export interface RevealConfig {
  transition: string
  transitionSpeed: string
  controls: boolean
  progress: boolean
  history: boolean
  center: boolean
  touch: boolean
  loop: boolean
  rtl: boolean
  shuffle: boolean
  fragments: boolean
  fragmentInURL: boolean
  embedded: boolean
  help: boolean
  showNotes: boolean
  autoSlide: number
  autoSlideStoppable: boolean
  mouseWheel: boolean
  hideAddressBar: boolean
  previewLinks: boolean
  backgroundTransition: string
}

export interface SlideContent {
  metadata: SlideMetadata
  content: string
  html?: string
}
