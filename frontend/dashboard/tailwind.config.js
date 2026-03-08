/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                dark: '#0B0C10',
                cardDark: 'rgba(31, 41, 55, 0.7)',
                neonGreen: '#66FCF1',
                mutedTeal: '#45A29E',
                lightGray: '#C5C6C7',
                alertRed: '#FF4136',
                warnOrange: '#FF851B',
            },
            fontFamily: {
                cyber: ['Inter', 'sans-serif'],
            }
        },
    },
    plugins: [],
}
