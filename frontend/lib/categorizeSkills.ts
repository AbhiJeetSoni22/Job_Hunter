export type SkillCategory =
  | "Frontend"
  | "Backend"
  | "Database"
  | "Cloud"
  | "AI/ML"
  | "Other";

export interface CategorizedSkills {
  category: SkillCategory;
  skills: string[];
}

const CATEGORY_KEYWORDS: Record<Exclude<SkillCategory, "Other">, string[]> = {
  Frontend: [
    "react", "vue", "angular", "html", "css", "javascript", "typescript",
    "next.js", "nextjs", "tailwind", "svelte", "webpack", "frontend", "redux",
    "figma", "ui", "ux", "sass", "scss",
  ],
  Backend: [
    "python", "java", "node", "express", "fastapi", "django", "flask", "go",
    "golang", "rust", "c++", "c#", "backend", "api", "spring", "ruby", "rails",
    "php", "laravel", "graphql", "rest",
  ],
  Database: [
    "sql", "postgresql", "postgres", "mysql", "mongodb", "redis", "database",
    "sqlite", "dynamodb", "prisma", "supabase", "firebase", "nosql",
  ],
  Cloud: [
    "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform", "cloud",
    "devops", "ci/cd", "github actions", "jenkins", "nginx", "linux", "vercel",
    "heroku", "netlify",
  ],
  "AI/ML": [
    "machine learning", "deep learning", "tensorflow", "pytorch", "nlp", "ai",
    "ml", "gemini", "llm", "data science", "pandas", "numpy", "scikit", "openai",
    "computer vision", "neural",
  ],
};

const CATEGORY_ORDER: SkillCategory[] = [
  "Frontend",
  "Backend",
  "Database",
  "Cloud",
  "AI/ML",
  "Other",
];

function matchCategory(skill: string): SkillCategory {
  const normalized = skill.toLowerCase();

  for (const category of CATEGORY_ORDER) {
    if (category === "Other") continue;
    const keywords = CATEGORY_KEYWORDS[category];
    if (keywords.some((kw) => normalized.includes(kw))) {
      return category;
    }
  }

  return "Other";
}

export function categorizeSkills(skills: string[]): CategorizedSkills[] {
  const buckets = new Map<SkillCategory, string[]>();

  for (const skill of skills) {
    const category = matchCategory(skill);
    const list = buckets.get(category) ?? [];
    list.push(skill);
    buckets.set(category, list);
  }

  return CATEGORY_ORDER.filter((cat) => buckets.has(cat)).map((category) => ({
    category,
    skills: buckets.get(category)!,
  }));
}

export function getResumeQuality(skillsCount: number): {
  label: string;
  color: "green" | "sky" | "amber" | "default";
  description: string;
} {
  if (skillsCount === 0) {
    return {
      label: "Needs Review",
      color: "amber",
      description: "No skills detected yet",
    };
  }
  if (skillsCount < 8) {
    return {
      label: "Building Profile",
      color: "sky",
      description: "Add more technical skills for better matches",
    };
  }
  if (skillsCount < 20) {
    return {
      label: "Good Coverage",
      color: "green",
      description: "Solid skill profile for AI matching",
    };
  }
  return {
    label: "Excellent Profile",
    color: "green",
    description: "Rich skill profile — strong match potential",
  };
}
