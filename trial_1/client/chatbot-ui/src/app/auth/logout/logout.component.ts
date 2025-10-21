import { Component, OnInit } from '@angular/core';
import { Auth, signOut } from '@angular/fire/auth';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-logout',
  standalone: true,
  imports: [CommonModule],
  template: '<p>Logging you out...</p>',
  styleUrls: ['./logout.component.css']
})
export class LogoutComponent implements OnInit {

  constructor(private auth: Auth, private router: Router) { }

  ngOnInit(): void {
    signOut(this.auth).then(() => {
      // Sign-out successful.
      console.log('User signed out');
      this.router.navigate(['/login']);
    }).catch((error) => {
      // An error happened.
      console.error('Sign out error:', error);
      // Even if there's an error, try to navigate to login
      this.router.navigate(['/login']);
    });
  }
}
