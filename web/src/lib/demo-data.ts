import type { ZPCard, ZPSession, ZPAction } from "@/types/zero-prompt";

export const DEMO_SPEED_MULTIPLIER = 8;

// ── 13 Demo Cards ─────────────────────────────────────────────────────────────
// Cards 1, 2, 4, 5, 6, 9 → GO (go_ready), Cards 3, 7, 8, 10, 12 → NO-GO, Cards 11, 13 → stays analyzing

export const DEMO_CARDS: ZPCard[] = [
  {
    card_id: "nutriplan-aADukT",
    video_id: "aADukThvjXQ",
    title: "NutriPlan — AI Meal Planning with Simplified Nutrition Tracking",
    status: "analyzing",
    score: 0,
    domain: "Health & Nutrition",
    video_summary: "Trainer Winny breaks down how to simplify nutrition without obsessive calorie counting. The video covers macro-based meal templates, free meal plan structures, and grocery shopping strategies that eliminate decision fatigue for fitness-focused users.",
    insights: [
      "Simplified macro tracking (protein/carb/fat ratios) removes the complexity barrier that causes 70% of nutrition app users to quit within 2 weeks",
      "Auto-generated weekly meal plans based on user goals and dietary preferences eliminate daily decision fatigue",
      "Integrated grocery list export from meal plans saves 45 minutes per week on shopping preparation",
    ],
    mvp_proposal: {
      app_name: "NutriPlan",
      core_feature: "AI-powered simplified meal planning with macro tracking, auto-generated weekly plans, and grocery list export",
      tech_stack: "FastAPI + Next.js + PostgreSQL + OpenAI API",
      key_pages: ["Meal Plan Dashboard", "Macro Calculator", "Grocery List", "Progress Tracker"],
      estimated_days: 5,
    },
  },
  {
    card_id: "spendsense-784610",
    video_id: "jNQXAC9IVRw",
    title: "SpendSense AI — Expense Tracking with AI Categorization",
    status: "analyzing",
    score: 0,
    domain: "Personal Finance",
    video_summary: "An in-depth tutorial on building an AI-powered personal finance app that automatically categorizes transactions using machine learning. The creator demonstrates Plaid integration and Recharts visualizations for spending breakdowns.",
    insights: [
      "AI auto-categorization saves users 15 minutes per week of manual entry and tagging",
      "Visual spending breakdowns with Recharts increase financial awareness and drive 60% retention",
      "Monthly savings goal tracking with push reminders creates habitual engagement loops",
    ],
    mvp_proposal: {
      app_name: "SpendSense AI",
      core_feature: "Automatic transaction categorization with ML and visual monthly spending reports",
      tech_stack: "FastAPI + Next.js + PostgreSQL + Redis + scikit-learn",
      key_pages: ["Spending Dashboard", "Transaction List", "Category Breakdown", "Savings Goals"],
      estimated_days: 6,
    },
  },
  {
    card_id: "pawpulse-784798",
    video_id: "9bZkp7q19f0",
    title: "PawPulse — Pet Health Monitoring with AI Symptom Checker",
    status: "analyzing",
    score: 0,
    domain: "Pet Health",
    video_summary: "A startup founder walks through building a pet health app that uses AI to assess symptoms from user descriptions and photos. The video covers vet knowledge base integration and how to handle medical disclaimers responsibly.",
    insights: [
      "AI symptom checker reduces unnecessary vet visits by 30% while catching real emergencies faster",
      "Photo-based diagnosis using CNN models identifies 85% of common skin and coat conditions accurately",
      "Vaccination and medication reminders drive daily app opens and cement habitual health tracking",
    ],
    mvp_proposal: {
      app_name: "PawPulse",
      core_feature: "AI pet symptom checker with photo diagnosis and vet visit recommendations",
      tech_stack: "FastAPI + Next.js + PostgreSQL + TensorFlow Lite",
      key_pages: ["Pet Profile", "Symptom Checker", "Health Timeline", "Vet Finder"],
      estimated_days: 5,
    },
    reason: "Veterinary liability risk too high. Medical-adjacent claims without professional oversight expose the platform to lawsuits. Regulatory pathway unclear.",
    reason_code: "liability_risk",
  },
  {
    card_id: "studymate-060111",
    video_id: "kJQP7kiw5Fk",
    title: "StudyMate Lite — AI Flashcard Generator with Spaced Repetition",
    status: "analyzing",
    score: 0,
    domain: "EdTech",
    video_summary: "A developer builds an AI-powered study tool that auto-generates flashcards from pasted text or uploaded PDFs using GPT and implements the SM-2 spaced repetition algorithm for optimal review scheduling.",
    insights: [
      "AI flashcard generation from any text source reduces study prep time from 2 hours to 5 minutes",
      "SM-2 spaced repetition algorithm improves long-term retention by 70% vs random review",
      "Import-from-PDF feature fills the key gap that both Anki and Quizlet have ignored for years",
    ],
    mvp_proposal: {
      app_name: "StudyMate Lite",
      core_feature: "AI flashcard generation from any text with SM-2 spaced repetition scheduling",
      tech_stack: "FastAPI + Next.js + SQLite + OpenAI API",
      key_pages: ["Deck Library", "Create Deck", "Study Session", "Progress Stats"],
      estimated_days: 4,
    },
  },
  {
    card_id: "fitquest-441200",
    video_id: "mZz9FBC0VwY",
    title: "FitQuest — AI Personal Trainer with Pose Detection",
    status: "analyzing",
    score: 0,
    domain: "Fitness",
    video_summary: "A computer vision engineer demonstrates building a browser-based AI fitness coach using MediaPipe for real-time pose detection. The video covers form correction feedback, rep counting, and workout logging — all running entirely on-device.",
    insights: [
      "On-device MediaPipe pose detection runs at 30fps in-browser with zero server costs or privacy risk",
      "Real-time form correction audio cues reduce injury risk by 45% compared to self-directed training",
      "Gamified streak system with workout achievements drives 3x weekly retention vs basic logging apps",
    ],
    mvp_proposal: {
      app_name: "FitQuest",
      core_feature: "Real-time AI pose detection for form correction with gamified workout tracking",
      tech_stack: "Next.js + MediaPipe + Web Audio API + Supabase",
      key_pages: ["Workout Library", "Live Session", "Progress Dashboard", "Achievement Badges"],
      estimated_days: 6,
    },
  },
  {
    card_id: "bookswap-551300",
    video_id: "pXvBjX2gW5L",
    title: "BookSwap — Neighborhood Book Exchange with Map",
    status: "analyzing",
    score: 0,
    domain: "Community",
    video_summary: "A community builder demonstrates creating a hyperlocal book-sharing platform with map-based discovery, user reputation scoring, and a simple barter system. The video emphasizes the sustainability angle and word-of-mouth growth potential.",
    insights: [
      "Map-first discovery reduces book search time from days to seconds and drives hyperlocal community bonds",
      "Give-a-book take-a-book model creates zero marginal cost per exchange and scales organically",
      "User reputation scores with book condition ratings build the trust layer essential for peer exchange",
    ],
    mvp_proposal: {
      app_name: "BookSwap",
      core_feature: "Map-based neighborhood book exchange with reputation scoring and exchange requests",
      tech_stack: "FastAPI + Next.js + PostgreSQL + Mapbox GL",
      key_pages: ["Map Discovery", "My Shelf", "Exchange Requests", "User Profile"],
      estimated_days: 5,
    },
  },
  {
    card_id: "mealprep-661400",
    video_id: "qYw9Zx3H4Mn",
    title: "MealPrep AI — Weekly Meal Planning with Grocery Lists",
    status: "analyzing",
    score: 0,
    domain: "Food Tech",
    video_summary: "A food tech entrepreneur walks through building an AI meal planning app that generates personalized weekly menus based on dietary preferences and auto-creates consolidated grocery lists. The video covers Spoonacular API integration and allergy filter logic.",
    insights: [
      "AI weekly meal planning eliminates daily decision fatigue and reduces food waste by 35%",
      "Auto-generated consolidated grocery lists cut shopping time in half and prevent duplicate purchases",
      "Dietary restriction filters with allergy warnings handle the legal requirements while building user trust",
    ],
    mvp_proposal: {
      app_name: "MealPrep AI",
      core_feature: "AI-generated weekly meal plans with automatic grocery list consolidation",
      tech_stack: "FastAPI + Next.js + PostgreSQL + Spoonacular API",
      key_pages: ["Weekly Planner", "Recipe Browser", "Grocery List", "Dietary Preferences"],
      estimated_days: 5,
    },
    reason: "Commodity market with zero defensibility. Recipe APIs are freely available. No meaningful AI differentiation over existing meal planning apps.",
    reason_code: "no_moat",
  },
  {
    card_id: "parkspot-771500",
    video_id: "rZa1Bk5NpQx",
    title: "ParkSpot — AI Parking Finder with Real-Time Availability",
    status: "analyzing",
    score: 0,
    domain: "Urban Mobility",
    video_summary: "A smart city developer demonstrates using sensor data and ML models to predict parking availability before drivers arrive. The video covers city API integrations, real-time map overlays, and the business model for city partnership revenue.",
    insights: [
      "AI parking availability prediction reduces circling time by 70% and cuts urban fuel waste significantly",
      "One-tap navigate-to-spot UX removes all friction and creates habitual daily usage for commuters",
      "City data API partnerships create a defensible data moat that app-only competitors cannot replicate",
    ],
    mvp_proposal: {
      app_name: "ParkSpot",
      core_feature: "AI-predicted parking availability with one-tap navigation and real-time map overlays",
      tech_stack: "FastAPI + Next.js + PostgreSQL + Google Maps API + ML prediction service",
      key_pages: ["Parking Map", "Spot Detail", "Navigation", "Saved Locations"],
      estimated_days: 6,
    },
    reason: "Requires massive real-time parking sensor data infrastructure. City partnership dependency creates unsustainable go-to-market timeline for MVP.",
    reason_code: "infra_dependency",
  },
  {
    card_id: "plantpal-881600",
    video_id: "sAb3Cd4EfGh",
    title: "PlantPal — AI Plant Care Assistant with Photo Diagnosis",
    status: "analyzing",
    score: 0,
    domain: "Plant Care",
    video_summary: "A plant enthusiast and developer builds an AI plant care app using PlantNet API for photo-based species identification and disease detection. The video showcases the calming UX design philosophy and personalized watering reminder system.",
    insights: [
      "PlantNet API photo identification achieves 92% species accuracy and enables instant care guide lookup",
      "Personalized watering schedules based on plant species and pot size reduce plant death rate by 60%",
      "Calming green aesthetic with gentle push reminders drives daily engagement without causing anxiety",
    ],
    mvp_proposal: {
      app_name: "PlantPal",
      core_feature: "AI photo-based plant diagnosis with personalized care schedules and health tracking",
      tech_stack: "FastAPI + Next.js + PostgreSQL + PlantNet API",
      key_pages: ["My Garden", "Plant Scanner", "Care Schedule", "Diagnosis History"],
      estimated_days: 4,
    },
  },
  {
    card_id: "soundscape-991700",
    video_id: "tBc5De6FgHi",
    title: "Soundscape — AI Ambient Sound Generator for Focus",
    status: "analyzing",
    score: 0,
    domain: "Productivity",
    video_summary: "An audio engineer and developer builds a science-backed ambient sound app using the Web Audio API for real-time multi-layer mixing. The video demonstrates AI adaptive soundscapes that evolve based on user work rhythm and time-of-day patterns.",
    insights: [
      "Web Audio API multi-layer mixing runs entirely in-browser at zero backend cost for unlimited concurrent users",
      "Binaural beats at 40Hz improve focus task performance by 28% per peer-reviewed neuroscience studies",
      "AI-adaptive soundscapes that shift with user work rhythm create a unique personalized experience competitors lack",
    ],
    mvp_proposal: {
      app_name: "Soundscape",
      core_feature: "AI-adaptive ambient sound mixing with binaural beats and focus session tracking",
      tech_stack: "Next.js + Web Audio API + Supabase (sessions only)",
      key_pages: ["Sound Mixer", "Focus Timer", "Session History", "Sound Library"],
      estimated_days: 3,
    },
    reason: "Pure content play with no technical moat. Existing apps (Calm, Noisli, Brain.fm) have years of content libraries. Late entry with no differentiation.",
    reason_code: "saturated_market",
  },
  {
    card_id: "routeopt-102800",
    video_id: "uCd7Ef8GhIj",
    title: "RouteOpt — Delivery Route Optimization with ML",
    status: "analyzing",
    score: 0,
    domain: "Logistics",
    video_summary: "A logistics engineer breaks down building an ML-powered delivery route optimization system using OR-Tools and real-time traffic data. The video covers vehicle routing problem algorithms and how to integrate with Google Maps Distance Matrix API.",
    insights: [
      "OR-Tools VRP solver reduces total delivery distance by 25-35% vs naive route planning for 10+ stops",
      "Real-time traffic re-routing using Google Maps Distance Matrix cuts late deliveries by 40%",
      "Driver mobile app with turn-by-turn navigation and stop confirmation closes the last-mile data loop",
    ],
    mvp_proposal: {
      app_name: "RouteOpt",
      core_feature: "ML-powered delivery route optimization with real-time traffic re-routing",
      tech_stack: "FastAPI + Next.js + PostgreSQL + OR-Tools + Google Maps API",
      key_pages: ["Route Planner", "Driver App", "Delivery Tracking", "Fleet Analytics"],
      estimated_days: 7,
    },
  },
  {
    card_id: "cryptofomo-990201",
    video_id: "hT_nvWreIhg",
    title: "CryptoFomo — Real-Time Crypto Price Prediction",
    status: "analyzing",
    score: 0,
    domain: "Crypto/Finance",
    video_summary: "A crypto trader pitches building a real-time cryptocurrency price prediction dashboard using LSTM neural networks and social sentiment analysis. The video claims 70%+ prediction accuracy on short-term price movements.",
    insights: [
      "LSTM price prediction claims are legally problematic — 'financial advice' liability without SEC registration",
      "Market already saturated with 50+ better-funded competitors including CoinGecko and Binance",
      "24/7 GPU inference for real-time predictions exceeds MVP infrastructure budget by 3x minimum",
    ],
    mvp_proposal: {
      app_name: "CryptoFomo",
      core_feature: "Real-time crypto price prediction dashboard with LSTM and sentiment analysis",
      tech_stack: "FastAPI + Next.js + PostgreSQL + TensorFlow + CoinGecko API",
      key_pages: ["Price Dashboard", "Prediction Alerts", "Portfolio Tracker", "Sentiment Feed"],
      estimated_days: 7,
    },
    reason: "Regulatory risk too high. SEC uncertainty makes price prediction claims legally dangerous. Market saturated with 50+ competitors. Infrastructure costs exceed MVP budget by 3x.",
    reason_code: "high_risk_regulatory",
  },
  {
    card_id: "weatherai-113900",
    video_id: "vDe9Fg0HiJk",
    title: "WeatherAI — Hyper-Local Weather Prediction with ML",
    status: "analyzing",
    score: 0,
    domain: "Weather",
    video_summary: "A meteorology data scientist demonstrates training a neighborhood-level weather prediction model using crowdsourced sensor data and historical patterns. The video covers data ingestion pipelines and the mobile alert system for hyperlocal storm warnings.",
    insights: [
      "Neighborhood-level precision beats national weather services by 3x for micro-climate accuracy",
      "Crowdsourced sensor network creates a self-reinforcing data flywheel that improves model accuracy over time",
      "Hyperlocal storm and frost alerts for gardeners and outdoor workers address an underserved high-value niche",
    ],
    mvp_proposal: {
      app_name: "WeatherAI",
      core_feature: "Hyper-local ML weather prediction with neighborhood-level alerts and sensor integration",
      tech_stack: "FastAPI + Next.js + PostgreSQL + PyTorch + OpenWeather API",
      key_pages: ["Hyperlocal Forecast", "Alert Settings", "Sensor Map", "Historical Trends"],
      estimated_days: 7,
    },
  },
];

// ── Timeline Event Type ─────────────────────────────────────────────

export type DemoTimelineEvent = {
  /** Milliseconds from demo start */
  time: number;
  /** Card state mutation — card_id is the lookup key */
  cardUpdate?: { card_id: string; status: ZPCard["status"]; score?: number } & Partial<Omit<ZPCard, "card_id" | "status" | "score">>;
  /** Action feed log entry */
  action?: Omit<ZPAction, "timestamp">;
  /** Session-level status change */
  sessionStatus?: ZPSession["status"];
};

// ══════════════════════════════════════════════════════════════════════════════
// TIMELINE DESIGN
//
// PHASE 1 (4000ms → ~88500ms): Discovery & Verdict (GO/NO-GO per card)
//   - 13 cards discover at ~8s intervals
//   - Cards 1, 2, 4, 5, 6, 9 → GO (go_ready) — [counter N/4]
//   - Cards 3, 7, 8, 10 → NO-GO (liability/moat/infra/saturation)
//   - Card 11 (RouteOpt) discovers, stays analyzing
//   - Card 12 (CryptoFomo) discovers, gets NO-GO at score 42.0
//   - Card 13 (WeatherAI) discovers, stays analyzing
//   - BUILD TRIGGERED after 4th GO (FitQuest @48500ms)
//
// PHASE 2 (50000ms → 92000ms): Auto-Build (runs in parallel with Phase 1 tail)
//   - NutriPlan: build_queued → code_gen → validate → github → deploy → deployed
//   - SpendSense: same cycle
//   - StudyMate, FitQuest, BookSwap, PlantPal stay in go_ready
//
// PHASE 3 (95000ms → 200000ms): Continued Exploration
//   - RouteOpt and WeatherAI continue analysis
//   - New YouTube searches fill action feed
//
// Card discovery times: D_N = 6500 + (N-1) × 8000ms
// D1=6500, D2=14500, D3=22500, D4=30500, D5=38500, D6=46500,
// D7=54500, D8=62500, D9=70500, D10=78500
// Verdicts: V_N = D_N + 10000ms
// GO counter: [N/4] — build triggers at 4th GO (FitQuest, V5=48500ms)
// ══════════════════════════════════════════════════════════════════════════════

export const DEMO_TIMELINE: DemoTimelineEvent[] = [

  // ═══════════════════════════════════════════════════════════════════════════
  // PHASE 1 — Discovery & Verdict (GO/NO-GO per card)
  // Build triggers after 4th GO card (FitQuest @48500ms) — runs in parallel.
  // ═══════════════════════════════════════════════════════════════════════════

  // ── Card 1: NutriPlan (discover @6500, verdict @16500) ────────────────────
  {
    time: 4000,
    action: { type: "explore", message: "YouTube search: 'how to simplify nutrition meal plan' — filter: Recently uploaded — 12 results" },
  },
  {
    time: 5000,
    action: { type: "explore", message: "Scanning trending health & fitness videos — filter: Recently uploaded..." },
  },
  {
    time: 6500,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: NutriPlan — AI Meal Planning with Simplified Nutrition Tracking" },
  },
  {
    time: 8000,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "analyzing", analysis_step: "insight", domain: "Health & Nutrition" },
  },
  {
    time: 8500,
    action: { type: "council", message: "Vibe Council evaluating NutriPlan — nutrition SaaS market analysis in parallel..." },
  },
  {
    time: 10000,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "analyzing", analysis_step: "papers", papers_found: 3 },
  },
  {
    time: 10500,
    action: { type: "council", message: "Architect: FastAPI + Next.js + PostgreSQL. OpenAI API for meal plan generation based on macro targets. Clean REST API for CRUD + AI endpoints." },
  },
  {
    time: 12000,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 12500,
    action: { type: "council", message: "Scout: Health & wellness app market at $7.8B. Simplified nutrition angle underserved — MyFitnessPal and Noom are complex. Clear gap for 'easy mode' meal planning." },
  },
  {
    time: 14000,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "analyzing", analysis_step: "compete", competitors_found: "3", saturation: "low" },
  },
  {
    time: 14500,
    action: { type: "council", message: "Catalyst: 'Simplified nutrition' is the killer hook — directly from the video. Macro-based templates eliminate calorie obsession. Grocery list auto-export drives daily utility." },
  },
  {
    time: 16500,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "go_ready", score: 83.7, domain: "Health & Nutrition" },
    action: { type: "verdict", message: "NutriPlan scored 83.7 → GO — highest score! Added to build queue [1/4]" },
  },

  // ── Card 2: SpendSense AI (discover @14500, verdict @24500) ──────────────
  {
    time: 12000,
    action: { type: "explore", message: "YouTube search: 'how to make expense tracker with ai' — filter: Recently uploaded — 9 results" },
  },
  {
    time: 13000,
    action: { type: "explore", message: "Analyzing video jNQXAC9IVRw — personal finance concept extracted..." },
  },
  {
    time: 14500,
    cardUpdate: { card_id: "spendsense-784610", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: SpendSense AI — Expense Tracking with AI Categorization" },
  },
  {
    time: 16000,
    cardUpdate: { card_id: "spendsense-784610", status: "analyzing", analysis_step: "insight", domain: "Personal Finance" },
  },
  {
    time: 16500,
    action: { type: "council", message: "Vibe Council evaluating SpendSense AI — cross-referencing fintech market data..." },
  },
  {
    time: 18000,
    cardUpdate: { card_id: "spendsense-784610", status: "analyzing", analysis_step: "papers", papers_found: 5 },
  },
  {
    time: 18500,
    action: { type: "council", message: "Architect: PostgreSQL for transactions, Redis for caching. ML categorization layer sits cleanly on top of classic CRUD — excellent separation of concerns." },
  },
  {
    time: 20000,
    cardUpdate: { card_id: "spendsense-784610", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 20500,
    action: { type: "council", message: "Guardian: Financial data requires encryption at rest + SOC2 compliance planning. Risk is manageable with proper design principles from day one." },
  },
  {
    time: 22000,
    cardUpdate: { card_id: "spendsense-784610", status: "analyzing", analysis_step: "compete", competitors_found: "4", saturation: "medium" },
  },
  {
    time: 22500,
    action: { type: "council", message: "Advocate: Monthly spending reports with visual Recharts breakdowns drive retention. Export-to-CSV is the power user feature that builds loyalty." },
  },
  {
    time: 24500,
    cardUpdate: { card_id: "spendsense-784610", status: "go_ready", score: 81.2, domain: "Personal Finance" },
    action: { type: "verdict", message: "SpendSense AI scored 81.2 → GO — top score so far [2/4]" },
  },

  // ── Card 3: PawPulse (discover @22500, verdict @32500) ───────────────────
  {
    time: 20000,
    action: { type: "explore", message: "YouTube search: 'how to build pet health app' — filter: Recently uploaded — 8 results" },
  },
  {
    time: 21000,
    action: { type: "explore", message: "Analyzing video 9bZkp7q19f0 — pet tech concept identified with symptom detection angle..." },
  },
  {
    time: 22500,
    cardUpdate: { card_id: "pawpulse-784798", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: PawPulse — Pet Health Monitoring with AI Symptom Checker" },
  },
  {
    time: 24000,
    cardUpdate: { card_id: "pawpulse-784798", status: "analyzing", analysis_step: "insight", domain: "Pet Health" },
  },
  {
    time: 24500,
    action: { type: "council", message: "Vibe Council evaluating PawPulse — red flags emerging in medical-adjacent AI space..." },
  },
  {
    time: 26000,
    cardUpdate: { card_id: "pawpulse-784798", status: "analyzing", analysis_step: "papers", papers_found: 4 },
  },
  {
    time: 26500,
    action: { type: "council", message: "Guardian: CRITICAL — AI veterinary advice without licensed professional oversight creates direct malpractice exposure. No disclaimer UX can mitigate lawsuit risk at scale." },
  },
  {
    time: 28000,
    cardUpdate: { card_id: "pawpulse-784798", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 28500,
    action: { type: "council", message: "Scout: FDA's Digital Health Center flagged similar AI symptom apps in 2025. Regulatory pathway requires 18-24 month approval process. MVP timeline is impossible under current rules." },
  },
  {
    time: 30000,
    cardUpdate: { card_id: "pawpulse-784798", status: "analyzing", analysis_step: "compete", competitors_found: "2", saturation: "low" },
  },
  {
    time: 30500,
    action: { type: "council", message: "Advocate: Users in distress will trust AI diagnosis over seeking real vet care. This creates direct harm responsibility — even prominent disclaimers cannot eliminate this risk." },
  },
  {
    time: 32500,
    cardUpdate: {
      card_id: "pawpulse-784798",
      status: "nogo",
      score: 45,
      reason: "Veterinary liability risk too high. Medical-adjacent claims without professional oversight expose the platform to lawsuits. Regulatory pathway unclear.",
      reason_code: "liability_risk",
    },
    action: { type: "verdict", message: "PawPulse scored 45 → NO-GO — veterinary liability risk too high, regulatory pathway unclear without licensed professional oversight" },
  },

  // ── Card 4: StudyMate Lite (discover @30500, verdict @40500) ─────────────
  {
    time: 28000,
    action: { type: "explore", message: "YouTube search: 'how to create flashcard app with ai' — filter: Recently uploaded — 14 results" },
  },
  {
    time: 29000,
    action: { type: "explore", message: "Analyzing video kJQP7kiw5Fk — EdTech concept with SM-2 spaced repetition algorithm..." },
  },
  {
    time: 30500,
    cardUpdate: { card_id: "studymate-060111", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: StudyMate Lite — AI Flashcard Generator with Spaced Repetition" },
  },
  {
    time: 32000,
    cardUpdate: { card_id: "studymate-060111", status: "analyzing", analysis_step: "insight", domain: "EdTech" },
  },
  {
    time: 32500,
    action: { type: "council", message: "Vibe Council evaluating StudyMate Lite — EdTech market deep dive..." },
  },
  {
    time: 34000,
    cardUpdate: { card_id: "studymate-060111", status: "analyzing", analysis_step: "papers", papers_found: 6 },
  },
  {
    time: 34500,
    action: { type: "council", message: "Architect: SM-2 algorithm is well-documented and low implementation risk. FastAPI + SQLite is perfectly sufficient for MVP scope." },
  },
  {
    time: 36000,
    cardUpdate: { card_id: "studymate-060111", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 36500,
    action: { type: "council", message: "Scout: EdTech market fragmented but sticky. AI-generated flashcards from any pasted text source fills a genuine gap that Anki and Quizlet both missed." },
  },
  {
    time: 38000,
    cardUpdate: { card_id: "studymate-060111", status: "analyzing", analysis_step: "compete", competitors_found: "5", saturation: "medium" },
  },
  {
    time: 38500,
    action: { type: "council", message: "Advocate: Distraction-free study mode is the UX differentiator. Dark mode + clean typography + progress tracking score 9/10 for student engagement." },
  },
  {
    time: 40500,
    cardUpdate: { card_id: "studymate-060111", status: "go_ready", score: 75.0, domain: "EdTech" },
    action: { type: "verdict", message: "StudyMate Lite scored 75.0 → GO — council approved [3/4]" },
  },

  // ── Card 5: FitQuest (discover @38500, verdict @48500) ───────────────────
  {
    time: 36000,
    action: { type: "explore", message: "YouTube search: 'how to build ai fitness trainer app' — filter: Recently uploaded — 15 results" },
  },
  {
    time: 37000,
    action: { type: "explore", message: "Analyzing video mZz9FBC0VwY — AI personal trainer concept with computer vision pose analysis..." },
  },
  {
    time: 38500,
    cardUpdate: { card_id: "fitquest-441200", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: FitQuest — AI Personal Trainer with Pose Detection" },
  },
  {
    time: 40000,
    cardUpdate: { card_id: "fitquest-441200", status: "analyzing", analysis_step: "insight", domain: "Fitness" },
  },
  {
    time: 40500,
    action: { type: "council", message: "Vibe Council evaluating FitQuest — computer vision feasibility assessment underway..." },
  },
  {
    time: 42000,
    cardUpdate: { card_id: "fitquest-441200", status: "analyzing", analysis_step: "papers", papers_found: 7 },
  },
  {
    time: 42500,
    action: { type: "council", message: "Architect: TensorFlow.js or MediaPipe handles real-time pose detection entirely in-browser. No backend ML infrastructure needed — dramatically reduces cost." },
  },
  {
    time: 44000,
    cardUpdate: { card_id: "fitquest-441200", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 44500,
    action: { type: "council", message: "Catalyst: Real-time form correction during workouts is genuinely disruptive. 'Gym membership alternative at $0/month' positioning could go viral on social." },
  },
  {
    time: 46000,
    cardUpdate: { card_id: "fitquest-441200", status: "analyzing", analysis_step: "compete", competitors_found: "6", saturation: "medium" },
  },
  {
    time: 46500,
    action: { type: "council", message: "Guardian: Camera permissions must be explicitly transparent. On-device processing guarantee required — no recording, no server uploads. Privacy-first is non-negotiable." },
  },
  {
    time: 48500,
    cardUpdate: { card_id: "fitquest-441200", status: "go_ready", score: 77.3, domain: "Fitness" },
    action: { type: "verdict", message: "FitQuest scored 77.3 → GO — [4/4] threshold reached! Auto-build sequence triggered for all queued GO cards." },
  },

  // ── Card 6: BookSwap (discover @46500, verdict @56500) ───────────────────
  {
    time: 44000,
    action: { type: "explore", message: "YouTube search: 'how to make book sharing app' — filter: Recently uploaded — 6 results" },
  },
  {
    time: 45000,
    action: { type: "explore", message: "Analyzing video pXvBjX2gW5L — community exchange platform concept with local map discovery..." },
  },
  {
    time: 46500,
    cardUpdate: { card_id: "bookswap-551300", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: BookSwap — Neighborhood Book Exchange with Map" },
  },
  {
    time: 48000,
    cardUpdate: { card_id: "bookswap-551300", status: "analyzing", analysis_step: "insight", domain: "Community" },
  },
  {
    time: 48500,
    action: { type: "council", message: "Vibe Council evaluating BookSwap — community platform analysis underway..." },
  },
  {
    time: 50000,
    cardUpdate: { card_id: "bookswap-551300", status: "analyzing", analysis_step: "papers", papers_found: 2 },
  },
  {
    time: 50500,
    action: { type: "council", message: "Scout: Sustainability angle resonates strongly with Gen Z. Book sharing = waste reduction + community building = powerful narrative with organic virality potential." },
  },
  {
    time: 52000,
    cardUpdate: { card_id: "bookswap-551300", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 52500,
    action: { type: "council", message: "Advocate: Map-first interface must be intuitive. Book condition ratings (1-5 stars) and user reputation scores build the trust layer essential for peer exchange." },
  },
  {
    time: 54000,
    cardUpdate: { card_id: "bookswap-551300", status: "analyzing", analysis_step: "compete", competitors_found: "2", saturation: "low" },
  },
  {
    time: 54500,
    action: { type: "council", message: "Catalyst: Simple concept but execution is everything. 'Goodwill economy' — give a book, take a book — resonates emotionally and drives word-of-mouth growth." },
  },
  {
    time: 56500,
    cardUpdate: { card_id: "bookswap-551300", status: "go_ready", score: 73.5, domain: "Community" },
    action: { type: "verdict", message: "BookSwap scored 73.5 → GO — added to go_ready [5]" },
  },

  // ── Card 7: MealPrep AI (discover @54500, verdict @64500) ────────────────
  {
    time: 52000,
    action: { type: "explore", message: "YouTube search: 'how to build meal planning app with ai' — filter: Recently uploaded — 11 results" },
  },
  {
    time: 53000,
    action: { type: "explore", message: "Analyzing video qYw9Zx3H4Mn — meal planning AI concept with automatic grocery list generation..." },
  },
  {
    time: 54500,
    cardUpdate: { card_id: "mealprep-661400", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: MealPrep AI — Weekly Meal Planning with Grocery Lists" },
  },
  {
    time: 56000,
    cardUpdate: { card_id: "mealprep-661400", status: "analyzing", analysis_step: "insight", domain: "Food Tech" },
  },
  {
    time: 56500,
    action: { type: "council", message: "Vibe Council evaluating MealPrep AI — commodity market defensibility analysis..." },
  },
  {
    time: 58000,
    cardUpdate: { card_id: "mealprep-661400", status: "analyzing", analysis_step: "papers", papers_found: 4 },
  },
  {
    time: 58500,
    action: { type: "council", message: "Scout: Spoonacular, Edamam, TheMealDB — recipe APIs are freely available to any competitor. Any dev can replicate this in 2 weeks. Zero data defensibility." },
  },
  {
    time: 60000,
    cardUpdate: { card_id: "mealprep-661400", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 60500,
    action: { type: "council", message: "Catalyst: No meaningful AI differentiation here. Mealime, Paprika, Plan to Eat — 10+ established apps with dedicated teams already own this space. We bring nothing new." },
  },
  {
    time: 62000,
    cardUpdate: { card_id: "mealprep-661400", status: "analyzing", analysis_step: "compete", competitors_found: "7", saturation: "medium" },
  },
  {
    time: 62500,
    action: { type: "council", message: "Guardian: Recipe API dependency means we have no moat, no proprietary data, and no switching costs. Any competitor with a better UX immediately captures our users." },
  },
  {
    time: 64500,
    cardUpdate: {
      card_id: "mealprep-661400",
      status: "nogo",
      score: 38,
      reason: "Commodity market with zero defensibility. Recipe APIs are freely available. No meaningful AI differentiation over existing meal planning apps.",
      reason_code: "no_moat",
    },
    action: { type: "verdict", message: "MealPrep AI scored 38 → NO-GO — commodity market, freely available APIs, no AI moat over established competitors" },
  },

  // ── Card 8: ParkSpot (discover @62500, verdict @72500) ───────────────────
  {
    time: 60000,
    action: { type: "explore", message: "YouTube search: 'how to create parking finder app' — filter: Recently uploaded — 10 results" },
  },
  {
    time: 61000,
    action: { type: "explore", message: "Analyzing video rZa1Bk5NpQx — urban mobility parking intelligence concept..." },
  },
  {
    time: 62500,
    cardUpdate: { card_id: "parkspot-771500", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: ParkSpot — AI Parking Finder with Real-Time Availability" },
  },
  {
    time: 64000,
    cardUpdate: { card_id: "parkspot-771500", status: "analyzing", analysis_step: "insight", domain: "Urban Mobility" },
  },
  {
    time: 64500,
    action: { type: "council", message: "Vibe Council evaluating ParkSpot — infrastructure dependency analysis underway..." },
  },
  {
    time: 66000,
    cardUpdate: { card_id: "parkspot-771500", status: "analyzing", analysis_step: "papers", papers_found: 3 },
  },
  {
    time: 66500,
    action: { type: "council", message: "Guardian: City sensor data partnerships require 12-24 month procurement cycles. Without existing city API access, real-time availability data simply does not exist for an MVP." },
  },
  {
    time: 68000,
    cardUpdate: { card_id: "parkspot-771500", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 68500,
    action: { type: "council", message: "Scout: SpotHero, ParkWhiz, and Google Maps already have real-time parking data with city partnerships. Without sensor infrastructure we are just an inferior information aggregator." },
  },
  {
    time: 70000,
    cardUpdate: { card_id: "parkspot-771500", status: "analyzing", analysis_step: "compete", competitors_found: "4", saturation: "medium" },
  },
  {
    time: 70500,
    action: { type: "council", message: "Architect: Real-time parking availability requires hardware partnerships or city API contracts — neither achievable in MVP timeline. The core value proposition is blocked by infrastructure." },
  },
  {
    time: 72500,
    cardUpdate: {
      card_id: "parkspot-771500",
      status: "nogo",
      score: 41,
      reason: "Requires massive real-time parking sensor data infrastructure. City partnership dependency creates unsustainable go-to-market timeline for MVP.",
      reason_code: "infra_dependency",
    },
    action: { type: "verdict", message: "ParkSpot scored 41 → NO-GO — city sensor infrastructure dependency makes MVP impossible without 12-24 month partnership pre-work" },
  },

  // ── Card 9: PlantPal (discover @70500, verdict @80500) ───────────────────
  {
    time: 68000,
    action: { type: "explore", message: "YouTube search: 'how to build plant care app with ai' — filter: Recently uploaded — 7 results" },
  },
  {
    time: 69000,
    action: { type: "explore", message: "Analyzing video sAb3Cd4EfGh — plant health AI with image recognition for disease detection..." },
  },
  {
    time: 70500,
    cardUpdate: { card_id: "plantpal-881600", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: PlantPal — AI Plant Care Assistant with Photo Diagnosis" },
  },
  {
    time: 72000,
    cardUpdate: { card_id: "plantpal-881600", status: "analyzing", analysis_step: "insight", domain: "Plant Care" },
  },
  {
    time: 72500,
    action: { type: "council", message: "Vibe Council evaluating PlantPal — plant care market analysis and image AI feasibility check..." },
  },
  {
    time: 74000,
    cardUpdate: { card_id: "plantpal-881600", status: "analyzing", analysis_step: "papers", papers_found: 3 },
  },
  {
    time: 74500,
    action: { type: "council", message: "Scout: Plant parent trend is massive — 30% of Gen Z identify as plant enthusiasts. 42M+ houseplants sold in 2024. This market is still early and growing fast." },
  },
  {
    time: 76000,
    cardUpdate: { card_id: "plantpal-881600", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 76500,
    action: { type: "council", message: "Architect: PlantNet API or a lightweight custom CNN handles photo diagnosis. Fast to integrate — can prototype disease detection in a single sprint." },
  },
  {
    time: 78000,
    cardUpdate: { card_id: "plantpal-881600", status: "analyzing", analysis_step: "compete", competitors_found: "3", saturation: "low" },
  },
  {
    time: 78500,
    action: { type: "council", message: "Advocate: Calming green aesthetic with gentle care reminders — never harsh alerts. Emotional design is the retention driver for this audience. Soothing UX wins." },
  },
  {
    time: 80500,
    cardUpdate: { card_id: "plantpal-881600", status: "go_ready", score: 82.4, domain: "Plant Care" },
    action: { type: "verdict", message: "PlantPal scored 82.4 → GO — highest score yet! Council unanimously enthusiastic. Added to go_ready [6]" },
  },

  // ── Card 10: Soundscape (discover @78500, verdict @88500) ────────────────
  {
    time: 76000,
    action: { type: "explore", message: "YouTube search: 'how to make ambient sound app' — filter: Recently uploaded — 13 results" },
  },
  {
    time: 77000,
    action: { type: "explore", message: "Analyzing video tBc5De6FgHi — adaptive ambient audio AI with user productivity pattern learning..." },
  },
  {
    time: 78500,
    cardUpdate: { card_id: "soundscape-991700", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: Soundscape — AI Ambient Sound Generator for Focus" },
  },
  {
    time: 80000,
    cardUpdate: { card_id: "soundscape-991700", status: "analyzing", analysis_step: "insight", domain: "Productivity" },
  },
  {
    time: 80500,
    action: { type: "council", message: "Vibe Council evaluating Soundscape — competitive saturation check in focus audio market..." },
  },
  {
    time: 82000,
    cardUpdate: { card_id: "soundscape-991700", status: "analyzing", analysis_step: "papers", papers_found: 5 },
  },
  {
    time: 82500,
    action: { type: "council", message: "Scout: Calm has $2B valuation with years of content, Noisli has 8 years of library, Brain.fm has neuroscience validation — these are entrenched players with insurmountable content moats." },
  },
  {
    time: 84000,
    cardUpdate: { card_id: "soundscape-991700", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 84500,
    action: { type: "council", message: "Catalyst: Web Audio API mixing is trivially replicable — any developer can fork this in a weekend. No technical moat, no content moat, no behavioral data moat. Nothing defensible." },
  },
  {
    time: 86000,
    cardUpdate: { card_id: "soundscape-991700", status: "analyzing", analysis_step: "compete", competitors_found: "4", saturation: "low" },
  },
  {
    time: 86500,
    action: { type: "council", message: "Guardian: Binaural beats health benefit claims require peer-reviewed validation specific to our implementation. General neuroscience studies do not cover custom implementations — legal exposure." },
  },
  {
    time: 88500,
    cardUpdate: {
      card_id: "soundscape-991700",
      status: "nogo",
      score: 44,
      reason: "Pure content play with no technical moat. Existing apps (Calm, Noisli, Brain.fm) have years of content libraries. Late entry with no differentiation.",
      reason_code: "saturated_market",
    },
    action: { type: "verdict", message: "Soundscape scored 44 → NO-GO — pure content play, no technical moat, late entry against entrenched players with years of content libraries" },
  },

  // ── Card 11: RouteOpt (discover @86500, stays analyzing) ─────────────────
  {
    time: 84000,
    action: { type: "explore", message: "YouTube search: 'how to build delivery route optimizer' — filter: Recently uploaded — 8 results" },
  },
  {
    time: 85000,
    action: { type: "explore", message: "Analyzing video uCd7Ef8GhIj — ML-powered logistics route optimization concept..." },
  },
  {
    time: 86500,
    cardUpdate: { card_id: "routeopt-102800", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: RouteOpt — Delivery Route Optimization with ML" },
  },
  {
    time: 88000,
    cardUpdate: { card_id: "routeopt-102800", status: "analyzing", analysis_step: "insight", domain: "Logistics" },
  },

  // ── Card 12: CryptoFomo (discover @88000, NO-GO @97500) ──────────────────
  {
    time: 86000,
    action: { type: "explore", message: "YouTube search: 'how to make crypto price prediction app' — filter: Recently uploaded — 23 results" },
  },
  {
    time: 87000,
    action: { type: "explore", message: "Analyzing video hT_nvWreIhg — crypto trading prediction dashboard concept..." },
  },
  {
    time: 88000,
    cardUpdate: { card_id: "cryptofomo-990201", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: CryptoFomo — Real-Time Crypto Price Prediction" },
  },
  {
    time: 89500,
    cardUpdate: { card_id: "cryptofomo-990201", status: "analyzing", analysis_step: "insight", domain: "Crypto/Finance" },
  },
  {
    time: 90000,
    action: { type: "council", message: "Vibe Council evaluating CryptoFomo — multiple critical red flags detected immediately..." },
  },
  {
    time: 91000,
    cardUpdate: { card_id: "cryptofomo-990201", status: "analyzing", analysis_step: "papers", papers_found: 1 },
  },
  {
    time: 91500,
    action: { type: "council", message: "Guardian: HIGH RISK — SEC regulatory uncertainty is extreme. 'Price prediction' claims likely constitute unlicensed financial advice. Legal liability is unacceptable for an MVP." },
  },
  {
    time: 92500,
    cardUpdate: { card_id: "cryptofomo-990201", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 93000,
    action: { type: "council", message: "Scout: Market saturated with 50+ better-funded competitors. CoinGecko, CryptoCompare, Binance, dozens more. Zero differentiation or moat identified — why would users switch?" },
  },
  {
    time: 94000,
    cardUpdate: { card_id: "cryptofomo-990201", status: "analyzing", analysis_step: "compete", competitors_found: "50+", saturation: "high" },
  },
  {
    time: 94500,
    action: { type: "council", message: "Architect: Real-time ML price prediction requires dedicated GPU cluster running 24/7. Infrastructure costs exceed MVP budget by 3×. The cost model is fundamentally broken." },
  },
  {
    time: 96000,
    action: { type: "council", message: "Catalyst: No real innovation present. Another price tracker adds zero value to users' lives. 'FOMO' in the name is an ethically questionable design pattern." },
  },
  {
    time: 97000,
    action: { type: "council", message: "Advocate: Crypto market volatility creates user anxiety, not trust. Prediction claims that prove wrong cause direct psychological harm. Cannot endorse this product direction." },
  },
  {
    time: 97500,
    cardUpdate: {
      card_id: "cryptofomo-990201",
      status: "nogo",
      score: 42.0,
      reason: "Regulatory risk too high. SEC uncertainty, market saturation (50+ competitors), infrastructure costs 3x over budget, ethical concerns with FOMO-based design.",
      reason_code: "high_risk_regulatory",
    },
    action: { type: "verdict", message: "CryptoFomo scored 42.0 → NO-GO — regulatory risk, market saturation, broken cost model, and ethical concerns disqualify this idea" },
  },

  // ── Card 13: WeatherAI (discover @96500, stays analyzing) ────────────────
  {
    time: 94000,
    action: { type: "explore", message: "YouTube search: 'how to build weather prediction app with ml' — filter: Recently uploaded — 5 results" },
  },
  {
    time: 95000,
    action: { type: "explore", message: "Analyzing video vDe9Fg0HiJk — hyper-local weather ML model concept with neighborhood-level precision..." },
  },
  {
    time: 96500,
    cardUpdate: { card_id: "weatherai-113900", status: "analyzing", score: 0, analysis_step: "transcript" },
    action: { type: "card", message: "New idea card: WeatherAI — Hyper-Local Weather Prediction with ML" },
  },
  {
    time: 98000,
    cardUpdate: { card_id: "weatherai-113900", status: "analyzing", analysis_step: "insight", domain: "Weather" },
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // PHASE 2 — Auto-Build Processing (50000ms → 92000ms, parallel with Phase 1)
  //
  // Build triggered by 4th GO card (FitQuest @48500ms).
  // NutriPlan and SpendSense build and deploy; StudyMate, FitQuest, BookSwap,
  // PlantPal remain in go_ready showing the queue continues.
  // Each build cycle: build_queued → building → deployed (~20 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // ── Build 1: NutriPlan (queued @50000, deployed @70000) ──────────────────
  {
    time: 50000,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "build_queued" },
    action: { type: "build", message: "Generating PRD and technical specification for NutriPlan — Meal Planning SaaS MVP..." },
  },
  {
    time: 53000,
    action: { type: "build", message: "PRD complete — 2,800 words, 10 user stories defined (meal plan CRUD, macro calculator, grocery export)" },
  },
  {
    time: 55000,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "building", build_step: "code_gen" },
    action: { type: "build", message: "Blueprint: 16 files planned — FastAPI backend + Next.js frontend + PostgreSQL nutrition schema + OpenAI integration" },
  },
  {
    time: 57500,
    action: { type: "build", message: "Code generation in progress — FastAPI meal plan API + PostgreSQL nutrition models + OpenAI prompt layer..." },
  },
  {
    time: 59000,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "building", build_step: "validate" },
  },
  {
    time: 60500,
    action: { type: "build", message: "Generated 16 files — code evaluation passed (quality score 91/100)" },
  },
  {
    time: 63500,
    action: { type: "build", message: "Docker build succeeded — image size 245MB" },
  },
  {
    time: 64000,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "building", build_step: "github" },
  },
  {
    time: 65500,
    action: { type: "deploy", message: "Pushing to GitHub..." },
  },
  {
    time: 67500,
    action: { type: "deploy", message: "CI tests passed (12/12) — deploying to DO App Platform..." },
  },
  {
    time: 68000,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "building", build_step: "deploy" },
  },
  {
    time: 70000,
    cardUpdate: { card_id: "nutriplan-aADukT", status: "deployed" },
    action: { type: "deploy", message: "NutriPlan deployed → https://nutriplan-aaduk.ondigitalocean.app — Meal Planning SaaS MVP live!" },
  },

  // ── Build 2: SpendSense AI (queued @72000, deployed @92000) ──────────────
  {
    time: 72000,
    cardUpdate: { card_id: "spendsense-784610", status: "build_queued" },
    action: { type: "build", message: "Generating PRD and technical specification for SpendSense AI..." },
  },
  {
    time: 75000,
    action: { type: "build", message: "PRD complete — 2,800 words, 12 user stories defined" },
  },
  {
    time: 77000,
    cardUpdate: { card_id: "spendsense-784610", status: "building", build_step: "code_gen" },
    action: { type: "build", message: "Blueprint: 16 files planned — complex finance data models + Plaid-ready transaction API layer" },
  },
  {
    time: 79500,
    action: { type: "build", message: "Code generation in progress — FastAPI transaction categorization ML layer + Recharts spend visualizations..." },
  },
  {
    time: 81000,
    cardUpdate: { card_id: "spendsense-784610", status: "building", build_step: "validate" },
  },
  {
    time: 82500,
    action: { type: "build", message: "Generated 16 files — code evaluation passed (quality score 91/100)" },
  },
  {
    time: 85500,
    action: { type: "build", message: "Docker build succeeded — image size 267MB" },
  },
  {
    time: 86000,
    cardUpdate: { card_id: "spendsense-784610", status: "building", build_step: "github" },
  },
  {
    time: 87500,
    action: { type: "deploy", message: "Pushing to GitHub..." },
  },
  {
    time: 89500,
    action: { type: "deploy", message: "CI tests passed (14/14) — deploying to DO App Platform..." },
  },
  {
    time: 90000,
    cardUpdate: { card_id: "spendsense-784610", status: "building", build_step: "deploy" },
  },
  {
    time: 92000,
    cardUpdate: { card_id: "spendsense-784610", status: "deployed" },
    action: { type: "deploy", message: "SpendSense AI deployed → https://spendsense-784610.ondigitalocean.app" },
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // PHASE 3 — Continued Exploration (95000ms → 200000ms)
  //
  // NutriPlan and SpendSense deployed. 4 GO apps in go_ready (StudyMate,
  // FitQuest, BookSwap, PlantPal). RouteOpt and WeatherAI continue analysis.
  // New YouTube searches and action feed activity through 200s.
  // ═══════════════════════════════════════════════════════════════════════════

  {
    time: 95000,
    action: { type: "build", message: "2 apps deployed. 4 GO cards queued — StudyMate Lite, FitQuest, BookSwap, PlantPal — auto-build continues..." },
  },

  // RouteOpt analysis continues
  {
    time: 100000,
    cardUpdate: { card_id: "routeopt-102800", status: "analyzing", analysis_step: "papers", papers_found: 4 },
  },
  {
    time: 101000,
    action: { type: "council", message: "Vibe Council evaluating RouteOpt — OR-Tools integration complexity and logistics market feasibility..." },
  },
  {
    time: 103000,
    cardUpdate: { card_id: "routeopt-102800", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 104000,
    action: { type: "council", message: "Architect: OR-Tools VRP solver integration is complex but well-documented. Real-time traffic via Google Maps Distance Matrix API adds meaningful cost per route query." },
  },
  {
    time: 106000,
    cardUpdate: { card_id: "routeopt-102800", status: "analyzing", analysis_step: "compete", competitors_found: "6", saturation: "medium" },
  },
  {
    time: 107000,
    action: { type: "council", message: "Scout: Route4Me, OptimoRoute, Circuit — enterprise logistics players. SMB segment is underserved but requires deep sales motion. Market is real but complex to penetrate." },
  },

  // WeatherAI analysis continues
  {
    time: 110000,
    cardUpdate: { card_id: "weatherai-113900", status: "analyzing", analysis_step: "papers", papers_found: 5 },
  },
  {
    time: 111000,
    action: { type: "council", message: "Vibe Council evaluating WeatherAI — crowdsourced sensor data cold-start problem analysis..." },
  },
  {
    time: 113000,
    cardUpdate: { card_id: "weatherai-113900", status: "analyzing", analysis_step: "brainstorm" },
  },
  {
    time: 114000,
    action: { type: "council", message: "Guardian: Crowdsourced sensor network has a critical 6-month cold-start problem — no data → no users → no data. Requires subsidized sensor hardware distribution to launch." },
  },
  {
    time: 116000,
    cardUpdate: { card_id: "weatherai-113900", status: "analyzing", analysis_step: "compete", competitors_found: "3", saturation: "low" },
  },
  {
    time: 117000,
    action: { type: "council", message: "Scout: Tomorrow.io and ClimaCell already offer neighborhood-level precision with $100M+ funding. Hyperlocal weather has massive data infrastructure costs that dwarf MVP budgets." },
  },

  // New exploration activity
  {
    time: 120000,
    action: { type: "explore", message: "YouTube search: 'how to build ai scheduling assistant' — filter: Recently uploaded — 9 results" },
  },
  {
    time: 122000,
    action: { type: "explore", message: "Analyzing new opportunity — AI meeting intelligence angle with automated scheduling..." },
  },
  {
    time: 125000,
    action: { type: "explore", message: "YouTube search: 'how to create legal contract analyzer' — filter: Recently uploaded — 7 results" },
  },
  {
    time: 127000,
    action: { type: "explore", message: "Scanning high-engagement creator content — legal AI space growing rapidly..." },
  },
  {
    time: 130000,
    action: { type: "explore", message: "YouTube search: 'how to build social commerce app' — filter: Recently uploaded — 14 results" },
  },
  {
    time: 133000,
    action: { type: "explore", message: "Analyzing video — live shopping creator tools concept..." },
  },
  {
    time: 136000,
    action: { type: "explore", message: "YouTube search: 'how to make ai resume builder' — filter: Recently uploaded — 11 results" },
  },
  {
    time: 138000,
    action: { type: "explore", message: "Evaluating candidate — ATS optimization has strong demand signal but competitive space..." },
  },
  {
    time: 141000,
    action: { type: "explore", message: "YouTube search: 'how to build micro saas tool' — filter: Recently uploaded — 16 results" },
  },
  {
    time: 143000,
    action: { type: "explore", message: "Scanning micro-SaaS opportunities — workflow automation niche emerging..." },
  },
  {
    time: 146000,
    action: { type: "build", message: "Build queue active — 4 GO apps awaiting: StudyMate Lite, FitQuest, BookSwap, PlantPal" },
  },
  {
    time: 150000,
    action: { type: "explore", message: "YouTube search: 'how to optimize last mile delivery' — filter: Recently uploaded — 8 results" },
  },
  {
    time: 152000,
    action: { type: "explore", message: "Analyzing opportunity — last-mile delivery space, RouteOpt comparison..." },
  },
  {
    time: 155000,
    action: { type: "explore", message: "YouTube search: 'how to automate code review with ai' — filter: Recently uploaded — 12 results" },
  },
  {
    time: 157000,
    action: { type: "explore", message: "High-signal candidate — developer tooling shows strong market traction..." },
  },
  {
    time: 160000,
    action: { type: "explore", message: "YouTube search: 'how to build mental health journal app' — filter: Recently uploaded — 10 results" },
  },
  {
    time: 162000,
    action: { type: "explore", message: "Evaluating mental health space — high impact, high regulatory scrutiny..." },
  },
  {
    time: 165000,
    action: { type: "explore", message: "YouTube search: 'how to create ai photo editor app' — filter: Recently uploaded — 18 results" },
  },
  {
    time: 167000,
    action: { type: "explore", message: "Scanning creator economy tools — photo AI market is crowded but growing..." },
  },
  {
    time: 170000,
    action: { type: "explore", message: "YouTube search: 'how to build inventory management system' — filter: Recently uploaded — 9 results" },
  },
  {
    time: 172000,
    action: { type: "explore", message: "Analyzing retail operations AI concept — SMB market segment..." },
  },
  {
    time: 175000,
    action: { type: "build", message: "6 GO cards total: NutriPlan (Meal Planning SaaS) & SpendSense deployed, StudyMate, FitQuest, BookSwap, PlantPal queued. 5 NO-GO cards filtered. Exploration continues." },
  },
  {
    time: 180000,
    action: { type: "explore", message: "YouTube search: 'how to make ai customer support chatbot' — filter: Recently uploaded — 15 results" },
  },
  {
    time: 182000,
    action: { type: "explore", message: "Scanning support automation space — heavily saturated but niche verticals emerging..." },
  },
  {
    time: 185000,
    action: { type: "explore", message: "YouTube search: 'how to build second brain app with ai' — filter: Recently uploaded — 11 results" },
  },
  {
    time: 187000,
    action: { type: "explore", message: "Analyzing second-brain space — Notion, Obsidian competitors well-funded..." },
  },
  {
    time: 190000,
    action: { type: "explore", message: "YouTube search: 'how to generate product descriptions with ai' — filter: Recently uploaded — 13 results" },
  },
  {
    time: 193000,
    action: { type: "explore", message: "Evaluating e-commerce AI tooling — strong demand signal, accessible market..." },
  },
  {
    time: 195000,
    action: { type: "explore", message: "YouTube search: 'how to track subscriptions and save money' — filter: Recently uploaded — 8 results" },
  },
  {
    time: 198000,
    action: { type: "explore", message: "New candidate under evaluation — strong overlap with SpendSense AI category..." },
  },
  {
    time: 200000,
    action: { type: "explore", message: "Exploration continues — monitoring for new opportunities beyond 200 ideas scanned..." },
  },
];
