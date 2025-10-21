import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Auth, signInWithCustomToken } from '@angular/fire/auth';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  phoneNumber: string = '';
  verificationCode: string = '';
  verificationSent: boolean = false;

  constructor(private http: HttpClient, private auth: Auth) { }

  sendVerificationCode() {
    this.http.get(`http://localhost:8080/send_verification_code/${this.phoneNumber}`).subscribe(() => {
      this.verificationSent = true;
    });
  }

  verifyCode() {
    this.http.post<{token: string}>('http://localhost:8080/verify_code', { phone_number: this.phoneNumber, code: this.verificationCode }).subscribe(response => {
      if (response.token) {
        signInWithCustomToken(this.auth, response.token)
          .then((userCredential) => {
            // Signed in
            const user = userCredential.user;
            console.log('User signed in:', user);
          })
          .catch((error) => {
            const errorCode = error.code;
            const errorMessage = error.message;
            console.error('Sign in error:', errorCode, errorMessage);
          });
      }
    });
  }
}
