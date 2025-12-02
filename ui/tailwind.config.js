/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: '#00d4ff',
                secondary: '#1a1a2e',
                accent: '#ff007a',
            },
        },
    },
    plugins: [],
}
