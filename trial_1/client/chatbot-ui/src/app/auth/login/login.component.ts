import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Auth, signInWithCustomToken } from '@angular/fire/auth';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  phoneNumber: string = '';
  verificationCode: string = '';
  verificationSent: boolean = false;
  loading: boolean = false;
  private apiUrl = environment.apiUrl

  constructor(private http: HttpClient, private auth: Auth, private router: Router) { }

  sendVerificationCode() {
    this.loading = true;
    this.http.get(`${this.apiUrl}/send_verification_code/${this.phoneNumber}`).subscribe(() => {
      this.verificationSent = true;
      this.loading = false;
    });
  }

  verifyCode() {
    this.loading = true;
    this.http.post<{token: string}>(`${this.apiUrl}/verify_code`, { phone_number: this.phoneNumber, code: this.verificationCode }).subscribe(response => {
      if (response.token) {
        signInWithCustomToken(this.auth, response.token)
          .then((userCredential) => {
            // Signed in
            const user = userCredential.user;
            console.log('User signed in:', user);

            // Send welcome message
            const messagePayload = {
              phone_number: user.uid,
              template_name: "welcome",
              params: {}
            };
            this.http.post(`${this.apiUrl}/send_template_whatsapp_message`, messagePayload)
              .subscribe({
                next: () => console.log('Welcome message sent successfully.'),
                error: (err) => console.error('Failed to send welcome message:', err)
              });

            this.router.navigate(['/main']);
          })
          .catch((error) => {
            const errorCode = error.code;
            const errorMessage = error.message;
            console.error('Sign in error:', errorCode, errorMessage);
            this.loading = false;
          });
      } else {
        this.loading = false;
      }
    });
  }
}
