declare module "katex/contrib/auto-render" {
  interface Delimiter {
    left: string;
    right: string;
    display: boolean;
  }

  interface AutoRenderOptions {
    delimiters?: Delimiter[];
    throwOnError?: boolean;
    ignoredTags?: string[];
    ignoredClasses?: string[];
  }

  export default function renderMathInElement(element: HTMLElement, options?: AutoRenderOptions): void;
}
