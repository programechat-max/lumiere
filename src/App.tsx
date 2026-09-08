import { useState, useCallback } from 'react';
import type { Page, TabKey, ChatMessage } from './types';
import { mockProfile, mockChatMessages, mockWorkoutProgram, mockMeals, mockDailyRings, mockWeightData } from './mockData';
import LoginScreen from './components/LoginScreen';
import RegisterScreen from './components/RegisterScreen';
import OnboardingWizard from './components/OnboardingWizard';
import FlowScreen from './components/FlowScreen';
import ChatScreen from './components/ChatScreen';
import DailyScreen from './components/DailyScreen';
import WorkoutScreen from './components/WorkoutScreen';
import NutritionScreen from './components/NutritionScreen';
import BottomNav from './components/BottomNav';
import SettingsPanel from './components/SettingsPanel';

function App() {
  const [page, setPage] = useState<Page>('login');
  const [activeTab, setActiveTab] = useState<TabKey>('flow');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(mockChatMessages);

  const handleLogin = useCallback(() => { setPage('dashboard'); setActiveTab('flow'); }, []);
  const handleRegister = useCallback(() => setPage('onboarding'), []);
  const handleOnboardingComplete = useCallback(() => { setPage('dashboard'); setActiveTab('flow'); }, []);
  const handleOnboardingSkip = useCallback(() => { setPage('dashboard'); setActiveTab('flow'); }, []);
  const handleLogout = useCallback(() => { setPage('login'); setSettingsOpen(false); }, []);
  const handleSendChat = useCallback((message: string) => {
    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: message, timestamp: new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }) };
    setChatMessages((prev) => [...prev, userMsg]);
    setTimeout(() => {
      const responses = ['Anladım! Mevcut programına bakarak en uygun cevabı hazırlıyorum.', 'Harika soru! Hedeflerine göre en iyi yaklaşımı belirleyelim.', 'Bugünkü ilerlemen iyi görünüyor. Devam et!', 'Bunu birlikte çözebiliriz. Önerilerimi hazırlıyorum.'];
      setChatMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), role: 'assistant', content: responses[Math.floor(Math.random() * responses.length)], timestamp: new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }) }]);
    }, 1200);
  }, []);

  if (page === 'login') return <LoginScreen onLogin={handleLogin} onGoRegister={() => setPage('register')} />;
  if (page === 'register') return <RegisterScreen onRegister={handleRegister} onGoLogin={() => setPage('login')} />;
  if (page === 'onboarding') return <OnboardingWizard onComplete={handleOnboardingComplete} onSkip={handleOnboardingSkip} />;

  return <div className="min-h-screen"><div className="max-w-md mx-auto min-h-screen relative">
    {activeTab === 'flow' && <FlowScreen profile={mockProfile} rings={mockDailyRings} onNavigate={setActiveTab} onOpenSettings={() => setSettingsOpen(true)} onLogout={handleLogout} onSendChat={handleSendChat} />}
    {activeTab === 'chat' && <ChatScreen messages={chatMessages} onSend={handleSendChat} />}
    {activeTab === 'daily' && <DailyScreen weightData={mockWeightData} rings={mockDailyRings} profile={mockProfile} />}
    {activeTab === 'workout' && <WorkoutScreen program={mockWorkoutProgram} />}
    {activeTab === 'nutrition' && <NutritionScreen meals={mockMeals} rings={mockDailyRings} />}
    <div className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md z-30"><BottomNav activeTab={activeTab} onTabChange={setActiveTab} /></div>
  </div><SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} onLogout={handleLogout} /></div>;
}

export default App;
