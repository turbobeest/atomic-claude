import adapterNode from '@sveltejs/adapter-node';
import adapterStatic from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const isStatic = process.env.BUILD_MODE === 'static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: isStatic
      ? adapterStatic({
          pages: 'build',
          assets: 'build',
          fallback: 'index.html',
          precompress: false,
          strict: false
        })
      : adapterNode(),
    paths: {
      base: isStatic ? '/audits' : ''
    },
    prerender: {
      entries: isStatic ? ['/'] : [],
      handleHttpError: 'warn',
      handleUnseenRoutes: 'ignore'
    }
  }
};

export default config;
