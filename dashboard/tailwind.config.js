/** @type {import('tailwindcss').Config} */
export default {
    darkMode: 'class',
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                "primary": "#ffd900",
                "background-light": "#f8f8f5",
                "background-dark": "#121212",
                "card-dark": "#1E1E1E",
                "border-dark": "#2A2A2A",
            },
            fontFamily: {
                "display": ["Inter", "sans-serif"]
            },
        },
    },
    plugins: [],
}
