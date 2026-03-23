pipeline {
    agent any
    
    environment {
        // Change this to your actual Docker Hub username!
        DOCKER_IMAGE = "YOUR_DOCKERHUB_USERNAME/securenoc-backend"
    }

    stages {
        stage('Checkout') {
            steps {
                // Pulls the code from the GitHub repo that triggered the webhook
                checkout scm
            }
        }
        
        stage('Automated Testing') {
            steps {
                echo "Running Python Pytest validation..."
                // We use Docker to spin up a temporary Python environment, mount the workspace, and run tests!
                sh '''
                    docker run --rm -v ${WORKSPACE}:/app -w /app python:3.10-slim /bin/sh -c "
                        pip install -r src/backend/requirements.txt &&
                        pip install pytest httpx &&
                        pytest src/backend/tests/
                    "
                '''
            }
        }
        
        stage('Build & Push Docker Image') {
            steps {
                echo "Building Docker Image..."
                sh "docker build -t ${DOCKER_IMAGE}:latest ./src/backend"
                
                echo "Pushing to Docker Hub..."
                // Requires you to add 'dockerhub-creds' in Jenkins Credentials
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', passwordVariable: 'DOCKER_PASS', usernameVariable: 'DOCKER_USER')]) {
                    sh "echo \$DOCKER_PASS | docker login -u \$DOCKER_USER --password-stdin"
                    sh "docker push ${DOCKER_IMAGE}:latest"
                }
            }
        }
        
        stage('Deploy to Kubernetes') {
            steps {
                echo "Applying Kubernetes Manifests..."
                sh "kubectl apply -f k8s/"
                
                echo "Triggering Rolling Update..."
                sh "kubectl rollout restart deployment backend"
            }
        }
    }
}
