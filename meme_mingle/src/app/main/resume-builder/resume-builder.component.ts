import { Component, OnInit } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormControl,
  FormArray,
  Validators
} from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import Docxtemplater from 'docxtemplater';
import PizZip from 'pizzip';
import PizZipUtils from 'pizzip/utils/index.js';
import { saveAs } from 'file-saver';
import { AppService } from 'src/app/app.service';
function loadFile(
  url: string,
  callback: (error: Error | null, content: string) => void
) {
  PizZipUtils.getBinaryContent(url, callback);
}

@Component({
  selector: 'app-resume-builder',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './resume-builder.component.html',
  styleUrls: ['./resume-builder.component.scss']
})
export class ResumeBuilderComponent implements OnInit {
  personForm!: FormGroup;

  createdResumeId: string | null = null;   // store the newly created resume ID
  enhancedResumeText: string | null = null; // store AI-improved text
  atsScore: number | null = null;           // store ATS score from AI
  isImproving = false;                      // UI flag to show "Enhancing..."
  activeTab = 'personal';
  currentStep = 1; // For progress indicator
  availableTabs = ['personal', 'education', 'experience', 'skills', 'projects'];
  formProgress = {
    personal: 0,
    education: 0,
    experience: 0,
    skills: 0,
    projects: 0
  };


  showSuccessDialog = false;
successDialogTitle = '';
successDialogMessage = '';
showResumeIdInDialog = false;
showAtsScoreInDialog = false;

showErrorDialog = false;
errorDialogTitle = '';
errorDialogMessage = '';
errorDetails = '';
errorRetryAction: (() => void) | null = null;

showInfoDialog = false;
infoDialogTitle = '';
infoDialogMessage = '';
infoDialogConfirmText = 'Confirm';
infoDialogConfirmIcon = 'fa-check';
infoDialogAction: (() => void) | null = null;

  constructor(
    private fb: FormBuilder,
    private appService: AppService
  ) {}

  ngOnInit(): void {
    this.personForm = this.fb.group({
      // Basic personal info
      fName: [''],
      lName: [''],
      description: [''],

      // Career
      career: [''],
      career2: [''],
      career3: [''],

      // Contact
      phoneNum: [''],
      email: [''],
      website: [''],

      // Instead of a single "socialmedia" field,
      // we store multiple social accounts in a FormArray:
      socialAccounts: this.fb.array([]),

      // Skills / Achievements
      skills: [''],
      achievements: [''],
      certifications: [''],

      // Dynamic sections (FormArrays)
      education: this.fb.array([this.createEducationItem()]),
      experience: this.fb.array([this.createExperienceItem()]),
      projects: this.fb.array([]), // Start empty or add initial item if desired
      references: this.fb.array([])
    });
  }

  // Dialog methods
showSuccess(title: string, message: string, showResumeId = false, showAtsScore = false) {
  this.successDialogTitle = title;
  this.successDialogMessage = message;
  this.showResumeIdInDialog = showResumeId;
  this.showAtsScoreInDialog = showAtsScore;
  this.showSuccessDialog = true;
}

showError(title: string, message: string, details = '', retryAction: (() => void) | null = null) {
  this.errorDialogTitle = title;
  this.errorDialogMessage = message;
  this.errorDetails = details;
  this.errorRetryAction = retryAction;
  this.showErrorDialog = true;
}

showInfo(title: string, message: string, confirmText = 'Confirm', confirmIcon = 'fa-check', action: (() => void) | null = null) {
  this.infoDialogTitle = title;
  this.infoDialogMessage = message;
  this.infoDialogConfirmText = confirmText;
  this.infoDialogConfirmIcon = confirmIcon;
  this.infoDialogAction = action;
  this.showInfoDialog = true;
}

closeDialog() {
  this.showSuccessDialog = false;
  this.showErrorDialog = false;
  this.showInfoDialog = false;
}

confirmInfoAction() {
  if (this.infoDialogAction) {
    this.infoDialogAction();
  }
  this.closeDialog();
}

retryErrorAction() {
  if (this.errorRetryAction) {
    this.errorRetryAction();
  }
  this.closeDialog();
}

  // --- Factory methods to create FormGroups for dynamic sections ---
  createEducationItem(): FormGroup {
    return this.fb.group({
      school: [''],
      grad: [''],
      major: ['']
    });
  }

  createExperienceItem(): FormGroup {
    return this.fb.group({
      exp_company: [''],
      exp_date: [''],
      exp_description: ['']
    });
  }

  createProjectItem(): FormGroup {
    return this.fb.group({
      projectName: [''],
      projectUrl: [''],
      projectDesc: ['']
    });
  }

  createReferenceItem(): FormGroup {
    return this.fb.group({
      refName: [''],
      refContact: ['']
    });
  }

  // Social accounts => each item has platform, handle, url
  createSocialAccount(): FormGroup {
    return this.fb.group({
      platform: [''],   // e.g. "LinkedIn"
      handle: [''],     // e.g. "@john_doe"
      link: ['']        // e.g. "https://www.linkedin.com/in/john-doe"
    });
  }

  // --- Getters for convenience in the template ---
  get educationControls() {
    return (this.personForm.get('education') as FormArray).controls;
  }
  get experienceControls() {
    return (this.personForm.get('experience') as FormArray).controls;
  }
  get projectControls() {
    return (this.personForm.get('projects') as FormArray).controls;
  }
  get referenceControls() {
    return (this.personForm.get('references') as FormArray).controls;
  }
  get socialAccountsControls() {
    return (this.personForm.get('socialAccounts') as FormArray).controls;
  }

  // --- Methods to add/remove items from each FormArray ---
  addEducation() {
    (this.personForm.get('education') as FormArray).push(
      this.createEducationItem()
    );
  }
  removeEducation(index: number) {
    (this.personForm.get('education') as FormArray).removeAt(index);
  }

  addExperience() {
    (this.personForm.get('experience') as FormArray).push(
      this.createExperienceItem()
    );
  }
  removeExperience(index: number) {
    (this.personForm.get('experience') as FormArray).removeAt(index);
  }

  addProject() {
    (this.personForm.get('projects') as FormArray).push(this.createProjectItem());
  }
  removeProject(index: number) {
    (this.personForm.get('projects') as FormArray).removeAt(index);
  }

  addReference() {
    (this.personForm.get('references') as FormArray).push(
      this.createReferenceItem()
    );
  }
  removeReference(index: number) {
    (this.personForm.get('references') as FormArray).removeAt(index);
  }

  addSocialAccount() {
    (this.personForm.get('socialAccounts') as FormArray).push(
      this.createSocialAccount()
    );
  }
  removeSocialAccount(index: number) {
    (this.personForm.get('socialAccounts') as FormArray).removeAt(index);
  }
  // Tab navigation methods
  setActiveTab(tab: string) {
    this.activeTab = tab;
  }
  
  goToNextTab() {
    const currentIndex = this.availableTabs.indexOf(this.activeTab);
    if (currentIndex < this.availableTabs.length - 1) {
      this.activeTab = this.availableTabs[currentIndex + 1];
    }
  }
  
  goToPreviousTab() {
    const currentIndex = this.availableTabs.indexOf(this.activeTab);
    if (currentIndex > 0) {
      this.activeTab = this.availableTabs[currentIndex - 1];
    }
  }
  
  isNextTabDisabled(): boolean {
    return this.availableTabs.indexOf(this.activeTab) === this.availableTabs.length - 1;
  }
  
  isPreviousTabDisabled(): boolean {
    return this.availableTabs.indexOf(this.activeTab) === 0;
  }
  
  // Helper for character count
  getCharacterCount(controlName: string): number {
    const control = this.personForm.get(controlName);
    return control && control.value ? control.value.length : 0;
  }
  
  // Helper for skills suggestions
  addSkill(skill: string) {
    const currentSkills = this.personForm.get('skills')?.value || '';
    if (!currentSkills.includes(skill)) {
      const updatedSkills = currentSkills ? `${currentSkills}, ${skill}` : skill;
      this.personForm.get('skills')?.setValue(updatedSkills);
    }
  }

  // *** (1) Submit => Save Resume to DB
  onSubmit() {
    const formData = this.personForm.value;

    // If your backend expects user_id from the front end, supply it (or use JWT on server side).
    formData.user_id = localStorage.getItem('user_id') || '12345';

    this.appService.createResume(formData).subscribe({
      next: (res) => {
        console.log('Resume created:', res);
        this.createdResumeId = res.resume_id;
        this.showSuccess(
          'Resume Created Successfully', 
          'Your resume has been saved to our database and is ready for enhancement.',
          true,
          false
        );
        this.enhancedResumeText = null; // reset if we had an old AI result
        this.atsScore = null;
        this.currentStep = 2;
      },
      error: (err) => {
        console.error('Error creating resume:', err);
        
        this.showError(
          'Resume Creation Failed',
          'We encountered a problem while saving your resume.',
          err.message || 'Unknown error',
          () => this.onSubmit() // Retry action
        );
      }
    });
  }

  // *** (2) Download Original => docxtemplater logic with user form
  downloadOriginalDocx() {
    // If the user hasn't even created or filled the form, we can still let them download the local doc...
    // If you want to only allow doc download after saving to DB, check if this.createdResumeId

    loadFile(
      '../assets/doc-templates/Resume.docx',
      (error, content) => {
        if (error) {
          console.error('Error loading template file:', error);
          return;
        }
        try {
          const zip = new PizZip(content);
          const doc = new Docxtemplater(zip, {
            paragraphLoop: true,
            linebreaks: true
          });

          const formVal = this.personForm.value;

          // For placeholders in your template:
          doc.render({
            fName: formVal.fName || '',
            lName: formVal.lName || '',
            description: formVal.description || '',
            career: formVal.career || '',
            career2: formVal.career2 || '',
            career3: formVal.career3 || '',
            phoneNum: formVal.phoneNum || '',
            email: formVal.email || '',
            website: formVal.website || '',
            socialAccounts: formVal.socialAccounts,
            skills: formVal.skills || '',
            achievements: formVal.achievements || '',
            certifications: formVal.certifications || '',
            education: formVal.education,
            experience: formVal.experience,
            projects: formVal.projects,
            references: formVal.references
          });

          const out = doc.getZip().generate({
            type: 'blob',
            mimeType:
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
          });

          saveAs(out, 'original_resume.docx');
        } catch (err) {
          console.error('Error rendering template:', err);
        }
      }
    );
  }

  // *** (3) Improve Resume => calls AI endpoint
  improveResume() {
    if (!this.createdResumeId) {
      this.showInfo(
        'Resume Required',
        'Please save your resume first before enhancing it.',
        'Save Resume',
        'fa-save',
        () => this.onSubmit()
      );
      return;
    }
    this.isImproving = true;

    this.appService.improveResume(this.createdResumeId).subscribe({
      next: (res) => {
        console.log('AI improved resume:', res);
        this.isImproving = false;
        this.enhancedResumeText = res.ai_enhanced_resume;
        this.atsScore = res.ats_score;
        this.showSuccess(
          'Resume Enhanced', 
          'Your resume has been improved with AI technology.',
          false,
          true
        );
        this.currentStep = 3;
      },
      error: (err) => {
        console.error('Failed to improve resume:', err);
        this.isImproving = false;
        this.showError(
          'Enhancement Failed',
          'We encountered a problem while enhancing your resume.',
          err.message || 'Unknown error',
          () => this.improveResume() // Retry action
        );
      }
    });
  }

  // *** (4) Download Enhanced => docxtemplater using the AI text
  downloadEnhancedDocx() {
    if (!this.enhancedResumeText) {
      this.showInfo(
        'Enhancement Required',
        'Please enhance your resume with AI before downloading the enhanced version.',
        'Enhance Now',
        'fa-magic',
        () => this.improveResume()
      );
      return;
    }

    loadFile(
      '../assets/doc-templates/Resume-2.docx',
      (error, content) => {
        if (error) {
          console.error('Error loading template file:', error);
          return;
        }
        try {
          const zip = new PizZip(content);
          const doc = new Docxtemplater(zip, {
            paragraphLoop: true,
            linebreaks: true
          });

          // Suppose the LLM just returns one big text block in 'ai_enhanced_resume'.
          // If it's structured text, you might parse it or do something fancier.
          // For now, let's just place it in a single placeholder, e.g. {improvedResume}

          doc.render({
            improvedResume: this.enhancedResumeText,
            atsScore: this.atsScore || 0
          });

          const out = doc.getZip().generate({
            type: 'blob',
            mimeType:
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
          });

          saveAs(out, 'enhanced_resume.docx');
          this.currentStep = 4; 
        } catch (err) {
          console.error('Error rendering template (enhanced):', err);
        }
      }
    );
  }
}