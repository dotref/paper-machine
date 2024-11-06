/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./src/**/*.{html,js,ts,jsx,tsx}"],
    theme: {
        extend: {
            borderColor: {
                border: 'hsl(var(--border))'
            }
        }
    },
    plugins: [],
}