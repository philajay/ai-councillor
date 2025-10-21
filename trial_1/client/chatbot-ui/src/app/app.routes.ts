import { Routes } from '@angular/router';
import { LoginComponent } from './auth/login/login.component';
import { LogoutComponent } from './auth/logout/logout.component';
import { MainComponent } from './main/main.component';
import { authGuard } from './auth/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'logout', component: LogoutComponent },
  { path: 'main', component: MainComponent, canActivate: [authGuard] },
  { path: '', redirectTo: '/main', pathMatch: 'full' },
];
