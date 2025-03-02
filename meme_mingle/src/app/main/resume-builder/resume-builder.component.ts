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

  constructor(private fb: FormBuilder) {}

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

  // --- Button that generates DOCX (using docxtemplater + pizzip) ---
  generate() {
    loadFile(
      '../assets/doc-templates/Color-block-resume.docx',
      (error, content) => {
        if (error) {
          console.error('Error loading file:', error);
          return;
        }
        try {
          const zip = new PizZip(content);
          const doc = new Docxtemplater(zip, {
            paragraphLoop: true,
            linebreaks: true
          });

          const formVal = this.personForm.value;
          // docxtemplater can handle arrays if your .docx template
          // has loops set up for them (e.g. {#education}...{/education})

          doc.render({
            fName: formVal.fName || 'N/A',
            lName: formVal.lName || 'N/A',
            description: formVal.description || '',

            career: formVal.career || '',
            career2: formVal.career2 || '',
            career3: formVal.career3 || '',

            phoneNum: formVal.phoneNum || '',
            email: formVal.email || '',
            website: formVal.website || '',

            // Social array => you'd handle similarly in the template:
            // {#socialAccounts}
            //   Platform: {platform}, Handle: {handle}, Link: {link}
            // {/socialAccounts}
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

          saveAs(out, 'GSW_resume.docx');
        } catch (err) {
          console.error('Error rendering the template:', err);
        }
      }
    );
  }

  onSubmit() {
    console.log(this.personForm.value);
  }
}
