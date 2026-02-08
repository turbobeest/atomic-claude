# Web Performance Metrics Quick Reference

> **Sources**:
> - https://web.dev/vitals/
> - https://developer.chrome.com/docs/lighthouse/
> - https://www.w3.org/webperf/
> **Extracted**: 2025-12-21
> **Refresh**: Annually

## Core Web Vitals (2024)

### LCP - Largest Contentful Paint
**What it measures**: Loading performance - time until largest content element renders

| Rating | Threshold |
|--------|-----------|
| Good | ≤ 2.5s |
| Needs Improvement | 2.5s - 4.0s |
| Poor | > 4.0s |

**Common causes of poor LCP:**
- Slow server response times
- Render-blocking JavaScript/CSS
- Slow resource load times
- Client-side rendering

**Optimization strategies:**
1. Use a CDN for static assets
2. Preload critical resources: `<link rel="preload">`
3. Optimize images (WebP, lazy loading)
4. Minimize critical CSS

### INP - Interaction to Next Paint
**What it measures**: Responsiveness - delay between user interaction and visual feedback

| Rating | Threshold |
|--------|-----------|
| Good | ≤ 200ms |
| Needs Improvement | 200ms - 500ms |
| Poor | > 500ms |

**Common causes of poor INP:**
- Long-running JavaScript tasks
- Large DOM size
- Excessive re-renders
- Main thread blocking

**Optimization strategies:**
1. Break up long tasks with `scheduler.yield()`
2. Use web workers for heavy computation
3. Debounce/throttle event handlers
4. Minimize DOM size (< 1400 nodes ideal)

### CLS - Cumulative Layout Shift
**What it measures**: Visual stability - unexpected layout shifts during page load

| Rating | Threshold |
|--------|-----------|
| Good | ≤ 0.1 |
| Needs Improvement | 0.1 - 0.25 |
| Poor | > 0.25 |

**Common causes of poor CLS:**
- Images without dimensions
- Ads, embeds without reserved space
- Dynamically injected content
- Web fonts causing FOIT/FOUT

**Optimization strategies:**
1. Always set width/height on images and videos
2. Reserve space for ads and embeds
3. Use `font-display: optional` or preload fonts
4. Avoid inserting content above existing content

---

## Additional Performance Metrics

### TTFB - Time to First Byte
**Target**: < 800ms (good), < 1.8s (acceptable)

Measures server response time. Optimize with:
- Edge caching / CDN
- Database query optimization
- Server-side caching

### FCP - First Contentful Paint
**Target**: < 1.8s (good), < 3.0s (acceptable)

First visible content renders. Improve with:
- Reduce server response time
- Remove render-blocking resources
- Preload critical fonts

### TBT - Total Blocking Time
**Target**: < 200ms (good), < 600ms (acceptable)

Sum of blocking time between FCP and TTI. Reduce by:
- Code splitting
- Removing unused JavaScript
- Optimizing third-party scripts

---

## Performance Budget Guidelines

### JavaScript Bundle Size
| Type | Budget |
|------|--------|
| Initial bundle | < 170KB (compressed) |
| Total JS | < 500KB (compressed) |
| Per-route chunk | < 50KB (compressed) |

### Image Optimization
| Format | Use Case |
|--------|----------|
| WebP | General images (30% smaller than JPEG) |
| AVIF | Modern browsers (50% smaller than JPEG) |
| SVG | Icons, logos, illustrations |
| PNG | Transparency required, simple graphics |

### Resource Hints
```html
<!-- DNS prefetch for third-party domains -->
<link rel="dns-prefetch" href="//api.example.com">

<!-- Preconnect for critical origins -->
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

<!-- Preload critical resources -->
<link rel="preload" href="/fonts/main.woff2" as="font" crossorigin>

<!-- Prefetch likely navigation targets -->
<link rel="prefetch" href="/next-page.html">
```

---

## Lighthouse Score Breakdown

| Category | Weight |
|----------|--------|
| First Contentful Paint | 10% |
| Speed Index | 10% |
| Largest Contentful Paint | 25% |
| Total Blocking Time | 30% |
| Cumulative Layout Shift | 25% |

**Score Ranges:**
- 90-100: Good (green)
- 50-89: Needs Improvement (orange)
- 0-49: Poor (red)

---
*This excerpt was curated for agent knowledge grounding.*
