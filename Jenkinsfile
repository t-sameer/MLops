pipeline {
    agent any
    
    environment {
        // Change to your actual Docker Hub username!
        DOCKER_IMAGE = "YOUR_DOCKERHUB_USERNAME/securenoc-backend"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build Docker Image') {
            steps {
                echo "Building Docker Image..."
                // We build the image FIRST so all Python dependencies are packaged inside
                sh "docker build -t ${DOCKER_IMAGE}:latest ./src/backend"
            }
        }
        
        stage('Automated Testing') {
            steps {
                echo "Running Pytest INSIDE the built image..."
                // We run a temporary container from the image we JUST built.
                // It already has your code and requirements installed!
                sh '''
                    docker run --rm ${DOCKER_IMAGE}:latest /bin/sh -c "
                        pip install pytest httpx && 
                        pytest tests/
                    "
                '''
            }
        }
        
        stage('Push Docker Image') {
            steps {
                echo "Pushing to Docker Hub..."
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', passwordVariable: 'DOCKER_PASS', usernameVariable: 'DOCKER_USER')]) {
                    sh "echo \$DOCKER_PASS | docker login -u \$DOCKER_USER --password-stdin"
                    sh "docker push ${DOCKER_IMAGE}:latest"
                }
            }
        }
        
        stage('Deploy to Kubernetes') {
            steps {
                echo "Applying Kubernetes Manifests..."
                sh "kubectl apply -f k8s/monitoring.yml"
                
                echo "Triggering Rolling Update..."
                sh "kubectl rollout restart deployment backend"
            }
        }
    }
}
