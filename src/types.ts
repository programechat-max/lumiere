export type Page = 'login' | 'register' | 'onboarding' | 'dashboard';
export type TabKey = 'flow' | 'chat' | 'daily' | 'workout' | 'nutrition';
export type MembershipTier = 'FREE' | 'PRO' | 'ELITE' | 'ELITE_PLUS';
export interface UserProfile { fullName: string; email: string; age: number; height: number; weight: number; targetWeight: number; goal: string; experience: string; activityLevel: string; membership: MembershipTier; memberSince: string; cameraPermission: boolean; micPermission: boolean; }
export interface ChatMessage { id: string; role: 'user' | 'assistant'; content: string; timestamp: string; }
export interface WorkoutDay { day: string; title: string; exercises: Exercise[]; completed: boolean; }
export interface Exercise { name: string; sets: number; reps: string; weight: string; rest: string; completed: boolean; }
export interface Meal { id: string; name: string; time: string; calories: number; protein: number; carbs: number; fat: number; logged: boolean; items: string[]; }
export interface DailyRing { label: string; current: number; target: number; unit: string; color: string; }
export interface WeightEntry { date: string; weight: number; }
export interface MembershipPlan { id: MembershipTier; name: string; badge: string; priceTry: number; priceUsd: number; period: string; popular: boolean; color: string; description: string; features: string[]; limits: string; }
