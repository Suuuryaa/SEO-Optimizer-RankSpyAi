import { useEffect, useRef } from 'react'

// Scroll-in reveal without an animation library. Content is visible by default;
// it only starts hidden when IntersectionObserver exists and the user has not
// asked for reduced motion (see .js-reveal rules in index.css).
const supported = typeof window !== 'undefined' && 'IntersectionObserver' in window
if (supported) document.documentElement.classList.add('js-reveal')

export function useReveal() {
  const ref = useRef(null)
  useEffect(() => {
    const root = ref.current
    if (!root) return
    const els = [...(root.classList?.contains('reveal') ? [root] : []), ...root.querySelectorAll('.reveal')]
    if (!supported) {
      els.forEach(el => el.classList.add('is-visible'))
      return
    }
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('is-visible')
          io.unobserve(e.target)
        }
      })
    }, { rootMargin: '0px 0px -8% 0px' })
    els.forEach(el => io.observe(el))
    return () => io.disconnect()
  }, [])
  return ref
}
