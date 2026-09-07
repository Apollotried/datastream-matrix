import { Navigate, Route, Routes } from 'react-router-dom'

import { GuestRoute, ProtectedRoute } from './routeGuards.jsx'
import { LoginPage } from '../features/auth/LoginPage.jsx'
import { DatasetDetailPage } from '../features/datasets/DatasetDetailPage.jsx'
import { DatasetListPage } from '../features/datasets/DatasetListPage.jsx'

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/datasets" replace />} />
      <Route
        path="/login"
        element={
          <GuestRoute>
            <LoginPage />
          </GuestRoute>
        }
      />
      <Route
        path="/datasets"
        element={
          <ProtectedRoute>
            <DatasetListPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/datasets/:datasetId"
        element={
          <ProtectedRoute>
            <DatasetDetailPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
