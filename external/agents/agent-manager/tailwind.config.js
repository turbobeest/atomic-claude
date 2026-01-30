/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				gray: {
					850: '#1a1f2e'
				}
			}
		}
	},
	plugins: [require('@tailwindcss/typography')]
};
