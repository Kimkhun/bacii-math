import type { Config } from "tailwindcss";
import plugin from "tailwindcss/plugin";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {},
  },
  plugins: [
    // `stylus:` — larger hit targets for touch/pen input (tablets, iPad +
    // Apple Pencil) without bloating buttons for precise mouse users.
    plugin(({ addVariant }) => {
      addVariant("stylus", "@media (pointer: coarse)");
    }),
  ],
};

export default config;
