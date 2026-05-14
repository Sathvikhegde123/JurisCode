import { Route, Routes } from 'react-router-dom';
import { AppLayout } from '@/layouts/AppLayout';
import { DashboardPage } from '@/pages/DashboardPage';
import { ChallengePage } from '@/pages/ChallengePage';
import { LandingPage } from '@/pages/LandingPage';
import { LearningHubPage } from '@/pages/LearningHubPage';
import { ModelsPage } from '@/pages/ModelsPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { PracticeArenaPage } from '@/pages/PracticeArenaWorkflowPage';
import { SessionsPage } from '@/pages/SessionsPage';

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/practice" element={<PracticeArenaPage />} />
        <Route path="/challenge" element={<ChallengePage />} />
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/models" element={<ModelsPage />} />
        <Route path="/learn" element={<LearningHubPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
