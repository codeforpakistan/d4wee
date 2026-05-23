"""
Google Classroom Student Resource Structure
Based on: https://developers.google.com/classroom/reference/rest/v1/courses.students

Student Resource:
{
  "courseId": string,
  "userId": string,
  "profile": {
    "id": string,
    "name": {
      "givenName": string,
      "familyName": string,
      "fullName": string
    },
    "emailAddress": string,
    "photoUrl": string,
    "permissions": [
      {
        "permission": enum (Permission)
      }
    ],
    "verifiedTeacher": boolean
  }
}

Key Fields:
- courseId: Identifier of the course (matches Course.google_id)
- userId: Identifier of the user (unique across Google)
- profile.id: Identifier of the user (same as userId)
- profile.name.fullName: Full name of the student
- profile.emailAddress: Email address
- profile.photoUrl: URL of profile photo
