import { Suspense, lazy } from 'react';
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const ShowcasePage = lazy(() => import('./pages/ShowcasePage'));
const SkillsPage = lazy(() => import('./pages/SkillsPage'));
const SkillDetailPage = lazy(() => import('./pages/SkillDetailPage'));
const WorkflowsPage = lazy(() => import('./pages/WorkflowsPage'));
const WorkflowDetailPage = lazy(() => import('./pages/WorkflowDetailPage'));
const NanobotChatPage = lazy(() => import('./pages/NanobotChatPage'));

function withSuspense(element: React.ReactElement) {
  return (
    <Suspense fallback={<div className="px-6 py-8 text-sm text-muted">Loading…</div>}>
      {element}
    </Suspense>
  );
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: withSuspense(<DashboardPage />) },
      { path: 'showcase', element: withSuspense(<ShowcasePage />) },
      { path: 'skills', element: withSuspense(<SkillsPage />) },
      { path: 'skills/:skillId', element: withSuspense(<SkillDetailPage />) },
      { path: 'workflows', element: withSuspense(<WorkflowsPage />) },
      { path: 'workflows/:workflowId', element: withSuspense(<WorkflowDetailPage />) },
      { path: 'nanobot', element: withSuspense(<NanobotChatPage />) },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
