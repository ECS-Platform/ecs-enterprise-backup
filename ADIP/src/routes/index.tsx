import { Routes, Route } from 'react-router-dom';
import { AppLayout } from '../components/layouts/AppLayout';
import { ExecutiveControlTower } from '../pages/ExecutiveControlTower';
import { DeliveryHub } from '../pages/DeliveryHub';
import { RequirementsHub } from '../pages/RequirementsHub';
import { ArchitectureHub } from '../pages/ArchitectureHub';
import { DevelopmentHub } from '../pages/DevelopmentHub';
import { TestingHub } from '../pages/TestingHub';
import { ReleaseCenter } from '../pages/ReleaseCenter';
import { ProductionCenter } from '../pages/ProductionCenter';
import { OperationsCenter } from '../pages/OperationsCenter';
import { GovernanceCenter } from '../pages/GovernanceCenter';
import { LearningHub } from '../pages/LearningHub';
import { Reports } from '../pages/Reports';
import { Administration } from '../pages/Administration';

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<ExecutiveControlTower />} />
        <Route path="delivery" element={<DeliveryHub />} />
        <Route path="requirements" element={<RequirementsHub />} />
        <Route path="architecture" element={<ArchitectureHub />} />
        <Route path="development" element={<DevelopmentHub />} />
        <Route path="testing" element={<TestingHub />} />
        <Route path="release" element={<ReleaseCenter />} />
        <Route path="production" element={<ProductionCenter />} />
        <Route path="operations" element={<OperationsCenter />} />
        <Route path="governance" element={<GovernanceCenter />} />
        <Route path="learning" element={<LearningHub />} />
        <Route path="reports" element={<Reports />} />
        <Route path="administration" element={<Administration />} />
      </Route>
    </Routes>
  );
}
