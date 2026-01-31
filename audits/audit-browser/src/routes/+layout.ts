import type { LayoutLoad } from './$types';
import { base } from '$app/paths';

export const load: LayoutLoad = async ({ fetch }) => {
  const response = await fetch(`${base}/data/audits.json`);
  const data = await response.json();

  return {
    navigation: data.navigation,
    stats: data.stats
  };
};

// Enable prerendering for static builds
export const prerender = true;
export const ssr = false;
