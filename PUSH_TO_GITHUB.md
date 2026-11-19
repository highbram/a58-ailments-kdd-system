# Pushing this project to GitHub (Group A58)

1. Create a free account at https://github.com and click New repository. Name it `a58-ailments-kdd-system`, leave it empty (no README), and create it.
2. In VS Code, open this `Implementations` folder, open the terminal, and run (replace YOUR-USERNAME):

```
git init
git add .
git commit -m "Group A58 Ailments KDD System prototype"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/a58-ailments-kdd-system.git
git push -u origin main
```

3. Give the repository link to the group leader to include in the submission.

Note on hosting: the system uses Flask with a local SQLite file, so it runs on a laptop with `python app.py`. Vercel hosts serverless apps and does not keep a local database file between requests, so putting this version on Vercel would need the database moved to Supabase or Neon first. For the presentation, running it on the laptop is the reliable option.
