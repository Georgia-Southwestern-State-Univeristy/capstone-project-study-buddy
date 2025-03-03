import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ResumeBuilderComponent } from './resume-builder.component';

@NgModule({
    imports: [
        BrowserModule,
        FormsModule,
        ReactiveFormsModule
    ],
    declarations: [
        ResumeBuilderComponent
    ],
    bootstrap: [ResumeBuilderComponent]
})

export class AppModule { }