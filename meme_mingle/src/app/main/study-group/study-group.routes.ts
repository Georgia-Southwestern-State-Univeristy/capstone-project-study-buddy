import { Routes } from '@angular/router';

export const StudyGroup_routes: Routes = [
    {
        path: '',
        loadComponent: () => import('./study-group.component').then((m) => m.StudyGroupComponent),
        children: [
            {
                path: '',
                redirectTo: 'create-group',
                pathMatch:'full'
            },
            {
                path:'create-group-post',
                loadComponent: () =>
                  import('./create-group-post/create-group-post.component').then((m) => m.CreateGroupPostComponent),
            },
            {
                path:'group-posts/:groupId',
                loadComponent: () =>
                  import('./group-posts-list/group-posts-list.component').then((m) => m.GroupPostsListComponent),
            },
            {
                path:'create-group',
                loadComponent: () =>
                  import('./study-group-create/study-group-create.component').then((m) => m.StudyGroupCreateComponent),
              },
              {
                path:'join-group',
                loadComponent: () =>
                  import('./join-group/join-group.component').then((m) => m.JoinGroupComponent),
              },
              {
                path:'edit-group-post',
                loadComponent: () =>
                    import('./edit-group-post/edit-group-post.component').then((m) => m.EditGroupPostComponent),
              }
           
        ]
    }
];
