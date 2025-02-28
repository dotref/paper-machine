/** @type {import('tailwindcss').Config} */
import withMT from "@material-tailwind/react/utils/withMT";

module.exports = withMT({
    content: ["./src/**/*.{html,js,ts,jsx,tsx}"],
    theme: {
        extend: {
            borderColor: {
                border: 'hsl(var(--border))'
            }
        }
    },
    plugins: [],
});