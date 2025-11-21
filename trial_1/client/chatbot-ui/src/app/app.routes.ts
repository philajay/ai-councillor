import { Routes } from '@angular/router';
import { LoginComponent } from './auth/login/login.component';
import { LogoutComponent } from './auth/logout/logout.component';
import { MainComponent } from './main/main.component';
import { authGuard } from './auth/auth.guard';
import { DocumentUploadComponent } from './users/document-upload/document-upload.component';
import { DashboardComponent } from './admin/dashboard/dashboard.component';
import { WorkflowComponent } from './admin/workflow/workflow.component';
import { ComingSoonComponent } from './components/coming-soon/coming-soon.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'logout', component: LogoutComponent },
  { path: 'main', component: MainComponent, canActivate: [authGuard] },
  { path: 'upload-documents', component: DocumentUploadComponent, canActivate: [authGuard] },
  { path: 'admin/dashboard', component: DashboardComponent },
  { path: 'admin/workflow', component: WorkflowComponent },
  { path: 'coming-soon', component: ComingSoonComponent },
  { path: '', redirectTo: '/main', pathMatch: 'full' },
];
