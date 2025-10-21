import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Auth } from '@angular/fire/auth';
import { Storage, ref, uploadBytesResumable, getDownloadURL } from '@angular/fire/storage';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatIconModule } from '@angular/material/icon';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, of, Subject } from 'rxjs';
import { finalize } from 'rxjs/operators';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Firestore, doc, setDoc } from '@angular/fire/firestore';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { FormsModule } from '@angular/forms';


interface Upload {
  file: File;
  progress$: Subject<number>;
  downloadURL: string | null;
  isComplete: boolean;
}

@Component({
  selector: 'app-document-upload',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatListModule,
    MatButtonModule,
    MatProgressBarModule,
    MatIconModule,
    MatDividerModule,
    MatProgressSpinnerModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule
  ],
  templateUrl: './document-upload.component.html',
  styleUrls: ['./document-upload.component.css']
})
export class DocumentUploadComponent {
  tags: string[] = [];
  courseId: string | null = null;
  uploads = new Map<string, Upload>();

  // State for data extraction
  isExtracting = false;
  extractedData: any | null = null;
  missingFields: string[] = [];
  showConfirmation = false;

  // State for scheduling
  showScheduler = false;
  isScheduling = false;
  selectedDate: Date | null = null;
  selectedTime: string | null = null;
  availableTimes: string[] = [];
  isRegistrationComplete = false;

  constructor(
    private auth: Auth,
    private storage: Storage,
    private router: Router,
    private http: HttpClient,
    private firestore: Firestore
  ) {
    this.generateTimeSlots();
    const navigation = this.router.getCurrentNavigation();
    const state = navigation?.extras.state as { tags: string[], courseId: string };
    if (state?.tags && state?.courseId) {
      this.tags = state.tags;
      this.courseId = state.courseId;
    } else {
      console.error('Required data (tags or courseId) not provided for document upload.');
    }
  }

  generateTimeSlots(): void {
    for (let h = 0; h < 24; h++) {
      for (let m = 0; m < 60; m += 15) {
        const hour = h.toString().padStart(2, '0');
        const minute = m.toString().padStart(2, '0');
        this.availableTimes.push(`${hour}:${minute}`);
      }
    }
  }

  get areAllUploadsComplete(): boolean {
    if (this.tags.length === 0) return false;
    return this.tags.every(tag => this.uploads.get(tag)?.isComplete);
  }

  onFileSelected(event: any, tag: string): void {
    const file: File = event.target.files[0];
    if (file) {
      this.uploads.set(tag, {
        file,
        progress$: new Subject<number>(),
        downloadURL: null,
        isComplete: false
      });
      this.uploadFile(tag);
    }
  }

  uploadFile(tag: string): void {
    const upload = this.uploads.get(tag);
    const user = this.auth.currentUser;

    if (!upload || !user || upload.isComplete) return;

    const fileExtension = upload.file.name.split('.').pop();
    const fileName = `${tag}.${fileExtension}`;
    const filePath = `uploads/${user.uid}/${fileName}`;
    const storageRef = ref(this.storage, filePath);
    const uploadTask = uploadBytesResumable(storageRef, upload.file);

    uploadTask.on('state_changed',
      (snapshot) => {
        const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100;
        upload.progress$.next(progress);
      },
      (error) => {
        console.error('Upload failed:', error);
        this.uploads.delete(tag);
      },
      async () => {
        const downloadURL = await getDownloadURL(uploadTask.snapshot.ref);
        const finalUpload = this.uploads.get(tag);
        if (finalUpload) {
          finalUpload.downloadURL = downloadURL;
          finalUpload.isComplete = true;
          finalUpload.progress$.complete();
        }
      }
    );
  }

  submitForExtraction(): void {
    this.isExtracting = true;
    this.missingFields = [];
    this.extractedData = null;

    const payload = this.tags.map(tag => ({
      url: this.uploads.get(tag)?.downloadURL,
      tag: tag
    }));

    this.http.post<any>('http://localhost:8080/extract-data', { "urls_and_tags": payload })
      .pipe(finalize(() => this.isExtracting = false))
      .subscribe(response => {
        const requiredFields = ["Name", "DOB", "SEX", "Address", "Zipcode", "State"];
        this.missingFields = requiredFields.filter(field => !response[field]);

        if (this.missingFields.length > 0) {
          this.showConfirmation = false;
        } else {
          this.extractedData = response;
          this.showConfirmation = true;
        }
      }, error => {
        console.error('Data extraction failed:', error);
        this.missingFields = ['An error occurred during data extraction. Please try again.'];
      });
  }

  confirmData(): void {
    this.showConfirmation = false;
    this.showScheduler = true;
  }

  editData(): void {
    this.showConfirmation = false;
  }

  async scheduleExam(): Promise<void> {
    const userPhone = this.auth.currentUser?.uid;
    if (!this.selectedDate || !this.selectedTime || !userPhone) {
      console.error('Cannot schedule exam, missing date, time, or user phone number.');
      return;
    }
    this.isScheduling = true;

    const [hours, minutes] = this.selectedTime.split(':');
    const examDateTime = new Date(this.selectedDate);
    examDateTime.setHours(parseInt(hours, 10), parseInt(minutes, 10));

    const userExamData = {
      ...this.extractedData,
      courseId: this.courseId,
      examDateTime: examDateTime.toISOString()
    };

    try {
      const docRef = doc(this.firestore, 'user-exam', userPhone);
      await setDoc(docRef, userExamData);
      console.log('Exam scheduled successfully!');
      this.isRegistrationComplete = true;
      this.showScheduler = false;
    } catch (error) {
      console.error('Error scheduling exam:', error);
    } finally {
      this.isScheduling = false;
    }
  }
}
