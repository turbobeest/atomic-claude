import type { PageLoad } from './$types';
import { base } from '$app/paths';

export const load: PageLoad = async ({ fetch }) => {
  const response = await fetch(`${base}/data/audits.json`);
  const data = await response.json();

  return {
    audits: data.audits,
    filterOptions: data.filterOptions
  };
};
