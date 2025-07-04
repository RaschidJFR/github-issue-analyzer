For the next array of Github issues in json format, read the title, body, and all comments.
Based on the problem being solved, the proposed approach, the conclusion, and next steps stated (if any), 
return a JSON with this structure, one item inside the array per issue analyzed:



```json
[
  {
    "number": 1234, // The issue number
    "issue_type": "One of: Bug, Security, Performance, Documentation, Feature Request, Other",
    "summary": "Concise TLDR of the whole conversation and its conclusion, found in the issue\'s body and comments. Included the agreed approach to solve the issue and next steps when available. Max length: 500 chars",
    "effort": 3,  // Judging by the conversation, a score from 1 to 5 according to this scale:
                  // 5 - Broad scope, unknowns, new design or infrastructure changes
                  // 4 - Multiple components or systems, some uncertainty
                  // 3 - Involves investigation, development, and testing
                  // 2 - Minor fix or adjustment with low risk
                  // 1 - One-liner or config change, very localized
  },
]
```

Limit your response to only the content of the JSON. No extra acknowledgements or formatting in your answer, just the plain JSON content, minified, and without back quotes.
