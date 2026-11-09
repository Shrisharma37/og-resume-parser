"""
Canonical taxonomy and alias mappings for technical skills parsing.
Pre-compiled set lookups provide O(1) membership validation.
"""

from typing import Dict, Set

# Canonical display representation by normalized lowercase lookup key
CANONICAL_SKILL_MAP: Dict[str, str] = {
    # Languages
    "python": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "c": "C",
    "golang": "Go",
    "go": "Go",
    "rust": "Rust",
    "java": "Java",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "ruby": "Ruby",
    "php": "PHP",
    "scala": "Scala",
    "r": "R",
    "sql": "SQL",
    "html": "HTML5",
    "html5": "HTML5",
    "css": "CSS3",
    "css3": "CSS3",
    "shell": "Bash/Shell",
    "bash": "Bash/Shell",
    
    # Frameworks & Libraries
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "angular": "Angular",
    "angularjs": "Angular",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "node": "Node.js",
    "express": "Express.js",
    "expressjs": "Express.js",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "dotnet": ".NET",
    ".net": ".NET",
    "asp.net": "ASP.NET",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",

    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "sqlite": "SQLite",
    "cassandra": "Cassandra",
    "elasticsearch": "Elasticsearch",
    "dynamodb": "DynamoDB",

    # Cloud & DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "azure": "Azure",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "ci/cd": "CI/CD",
    "jenkins": "Jenkins",
    "github actions": "GitHub Actions",

    # Developer Tools
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "jira": "Jira",
    "postman": "Postman",
    "linux": "Linux",
    "vim": "Vim",
    "webpack": "Webpack",
    "vite": "Vite",
}

# Explicit categories mapped to canonical representations
SKILL_TAXONOMY: Dict[str, Set[str]] = {
    "languages": {
        "Python", "JavaScript", "TypeScript", "C++", "C#", "C", "Go", "Rust",
        "Java", "Kotlin", "Swift", "Ruby", "PHP", "Scala", "R", "SQL",
        "HTML5", "CSS3", "Bash/Shell"
    },
    "frameworks_libraries": {
        "React", "Vue.js", "Angular", "Next.js", "Node.js", "Express.js",
        "Django", "Flask", "FastAPI", "Spring Boot", ".NET", "ASP.NET",
        "PyTorch", "TensorFlow", "Keras", "Pandas", "NumPy", "Scikit-Learn"
    },
    "databases": {
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Cassandra",
        "Elasticsearch", "DynamoDB"
    },
    "cloud_devops": {
        "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform",
        "Ansible", "CI/CD", "Jenkins", "GitHub Actions"
    },
    "developer_tools": {
        "Git", "GitHub", "GitLab", "Jira", "Postman", "Linux", "Vim",
        "Webpack", "Vite"
    }
}