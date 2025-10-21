import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

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

  constructor(private http: HttpClient) { }

  sendVerificationCode() {
    this.http.get(`http://localhost:8080/send_verification_code/${this.phoneNumber}`).subscribe(() => {
      this.verificationSent = true;
    });
  }

  verifyCode() {
    this.http.post('http://localhost:8080/verify_code', { phone_number: this.phoneNumber, code: this.verificationCode }).subscribe(response => {
      console.log(response);
      // Handle successful verification
    });
  }
}
