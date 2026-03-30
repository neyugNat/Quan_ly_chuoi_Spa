import { createContext, useContext, useState, useEffect, ReactNode } from "react";

export interface ThemeConfig {
  id: string;
  name: string;
  emoji: string;
  sidebar: string;
  bg: string;
  accent: string;
  accentHover: string;
  accentText: string;
  ring: string;
}

export const themes: ThemeConfig[] = [
  {
    id: "aurora",
    name: "Aurora",
    emoji: "🌌",
    sidebar: "linear-gradient(165deg, #1e1b4b 0%, #312e81 45%, #1e3a8a 100%)",
    bg: "radial-gradient(ellipse at 0% 0%, rgba(167,139,250,0.25) 0px, transparent 55%), radial-gradient(ellipse at 100% 0%, rgba(96,165,250,0.2) 0px, transparent 55%), radial-gradient(ellipse at 50% 100%, rgba(52,211,153,0.15) 0px, transparent 55%), #f3f0ff",
    accent: "#6d28d9",
    accentHover: "#7c3aed",
    accentText: "text-violet-700",
    ring: "#ede9fe",
  },
  {
    id: "ocean",
    name: "Đại Dương",
    emoji: "🌊",
    sidebar: "linear-gradient(165deg, #0c4a6e 0%, #075985 45%, #1d4ed8 100%)",
    bg: "radial-gradient(ellipse at 0% 0%, rgba(56,189,248,0.2) 0px, transparent 55%), radial-gradient(ellipse at 100% 0%, rgba(99,102,241,0.15) 0px, transparent 55%), radial-gradient(ellipse at 50% 100%, rgba(34,211,238,0.15) 0px, transparent 55%), #eff8ff",
    accent: "#0369a1",
    accentHover: "#0284c7",
    accentText: "text-sky-700",
    ring: "#e0f2fe",
  },
  {
    id: "sunset",
    name: "Hoàng Hôn",
    emoji: "🌅",
    sidebar: "linear-gradient(165deg, #4c0519 0%, #7c2d12 40%, #78350f 70%, #713f12 100%)",
    bg: "radial-gradient(ellipse at 0% 0%, rgba(252,165,50,0.2) 0px, transparent 55%), radial-gradient(ellipse at 100% 0%, rgba(251,113,133,0.2) 0px, transparent 55%), radial-gradient(ellipse at 50% 100%, rgba(167,139,250,0.15) 0px, transparent 55%), #fff8f0",
    accent: "#c2410c",
    accentHover: "#ea580c",
    accentText: "text-orange-700",
    ring: "#ffedd5",
  },
  {
    id: "forest",
    name: "Rừng Xanh",
    emoji: "🌿",
    sidebar: "linear-gradient(165deg, #064e3b 0%, #065f46 45%, #134e4a 100%)",
    bg: "radial-gradient(ellipse at 0% 0%, rgba(52,211,153,0.2) 0px, transparent 55%), radial-gradient(ellipse at 100% 0%, rgba(56,189,248,0.15) 0px, transparent 55%), radial-gradient(ellipse at 50% 100%, rgba(167,243,208,0.2) 0px, transparent 55%), #f0fdf6",
    accent: "#047857",
    accentHover: "#059669",
    accentText: "text-emerald-700",
    ring: "#d1fae5",
  },
  {
    id: "rose",
    name: "Hoa Hồng",
    emoji: "🌸",
    sidebar: "linear-gradient(165deg, #500724 0%, #881337 45%, #6b21a8 100%)",
    bg: "radial-gradient(ellipse at 0% 0%, rgba(251,113,133,0.2) 0px, transparent 55%), radial-gradient(ellipse at 100% 0%, rgba(167,139,250,0.18) 0px, transparent 55%), radial-gradient(ellipse at 50% 100%, rgba(252,165,165,0.15) 0px, transparent 55%), #fff0f6",
    accent: "#be185d",
    accentHover: "#db2777",
    accentText: "text-pink-700",
    ring: "#fce7f3",
  },
];

export const wallpapers = [
  { id: "none", name: "Không có", preview: "", style: { background: "white" } },
  {
    id: "gradient1",
    name: "Bình Minh",
    style: { background: "linear-gradient(135deg, #f093fb 0%, #f5576c 50%, #4facfe 100%)" },
  },
  {
    id: "gradient2",
    name: "Xanh Biển",
    style: { background: "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)" },
  },
  {
    id: "gradient3",
    name: "Cánh Đồng",
    style: { background: "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)" },
  },
  {
    id: "gradient4",
    name: "Hoàng Kim",
    style: { background: "linear-gradient(135deg, #f7971e 0%, #ffd200 100%)" },
  },
  {
    id: "gradient5",
    name: "Mây Hồng",
    style: { background: "linear-gradient(135deg, #ee9ca7 0%, #ffdde1 100%)" },
  },
  {
    id: "mesh1",
    name: "Aurora Mesh",
    style: {
      background:
        "radial-gradient(at 40% 20%, hsla(28,100%,74%,1) 0px, transparent 50%), radial-gradient(at 80% 0%, hsla(189,100%,56%,1) 0px, transparent 50%), radial-gradient(at 0% 50%, hsla(355,100%,93%,1) 0px, transparent 50%), radial-gradient(at 80% 50%, hsla(340,100%,76%,1) 0px, transparent 50%), radial-gradient(at 0% 100%, hsla(22,100%,77%,1) 0px, transparent 50%), radial-gradient(at 80% 100%, hsla(242,100%,70%,1) 0px, transparent 50%), radial-gradient(at 0% 0%, hsla(343,100%,76%,1) 0px, transparent 50%)",
    },
  },
  {
    id: "mesh2",
    name: "Cosmic",
    style: {
      background:
        "radial-gradient(at 40% 20%, hsla(260,100%,70%,1) 0px, transparent 50%), radial-gradient(at 80% 0%, hsla(220,100%,56%,1) 0px, transparent 50%), radial-gradient(at 0% 50%, hsla(290,100%,60%,1) 0px, transparent 50%), radial-gradient(at 80% 50%, hsla(200,100%,70%,1) 0px, transparent 50%), radial-gradient(at 0% 100%, hsla(250,100%,65%,1) 0px, transparent 50%)",
    },
  },
];

export const languages = [
  { id: "vi", name: "Tiếng Việt", flag: "🇻🇳" },
  { id: "en", name: "English", flag: "🇬🇧" },
  { id: "zh", name: "中文", flag: "🇨🇳" },
  { id: "ja", name: "日本語", flag: "🇯🇵" },
];

interface ThemeContextType {
  theme: ThemeConfig;
  setThemeId: (id: string) => void;
  wallpaper: string;
  setWallpaper: (id: string) => void;
  language: string;
  setLanguage: (id: string) => void;
  density: "compact" | "comfortable" | "spacious";
  setDensity: (d: "compact" | "comfortable" | "spacious") => void;
  notifications: { email: boolean; push: boolean; sound: boolean; reports: boolean };
  setNotification: (key: string, val: boolean) => void;
  colorMode: "light" | "dark" | "system";
  setColorMode: (m: "light" | "dark" | "system") => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextType | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themeId, setThemeId] = useState(() => localStorage.getItem("spa_theme_id") || "aurora");
  const [wallpaper, setWallpaper] = useState(() => localStorage.getItem("spa_wallpaper") || "none");
  const [language, setLanguage] = useState(() => localStorage.getItem("spa_language") || "vi");
  const [density, setDensity] = useState<"compact" | "comfortable" | "spacious">(() => 
    (localStorage.getItem("spa_density") as any) || "comfortable"
  );
  const [notifications, setNotifications] = useState(() => {
    const saved = localStorage.getItem("spa_notifications");
    return saved ? JSON.parse(saved) : { email: true, push: true, sound: false, reports: true };
  });
  const [colorMode, setColorMode] = useState<"light" | "dark" | "system">(() => 
    (localStorage.getItem("spa_color_mode") as any) || "light"
  );
  const [isDark, setIsDark] = useState(false);

  // Persistence
  useEffect(() => {
    localStorage.setItem("spa_theme_id", themeId);
    localStorage.setItem("spa_wallpaper", wallpaper);
    localStorage.setItem("spa_language", language);
    localStorage.setItem("spa_density", density);
    localStorage.setItem("spa_notifications", JSON.stringify(notifications));
    localStorage.setItem("spa_color_mode", colorMode);
  }, [themeId, wallpaper, language, density, notifications, colorMode]);

  // Apply dark class to <html> based on colorMode
  useEffect(() => {
    const html = document.documentElement;
    const applyDark = (dark: boolean) => {
      if (dark) html.classList.add("dark");
      else html.classList.remove("dark");
      setIsDark(dark);
    };

    if (colorMode === "dark") { applyDark(true); return; }
    if (colorMode === "light") { applyDark(false); return; }
    // system
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    applyDark(mq.matches);
    const listener = (e: MediaQueryListEvent) => applyDark(e.matches);
    mq.addEventListener("change", listener);
    return () => mq.removeEventListener("change", listener);
  }, [colorMode]);

  const theme = themes.find((t) => t.id === themeId) || themes[0];

  const setNotification = (key: string, val: boolean) =>
    setNotifications((prev: any) => ({ ...prev, [key]: val }));

  return (
    <ThemeContext.Provider value={{
      theme, setThemeId,
      wallpaper, setWallpaper,
      language, setLanguage,
      density, setDensity,
      notifications, setNotification,
      colorMode, setColorMode,
      isDark,
    }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}
