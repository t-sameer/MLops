pipeline {
    agent any
    
    environment {
        // Change to your actual Docker Hub username!
        DOCKER_IMAGE = "tsameer/securenoc-backend"
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
                echo "Downloading kubectl tool..."
                sh '''
                    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
                    chmod +x ./kubectl
                '''
                
                echo "Patching Kubeconfig for Docker-to-Host networking..."
                sh '''
                    cp /root/.kube/config ./jenkins-kubeconfig
                    sed -i 's/0.0.0.0/172.17.0.1/g' ./jenkins-kubeconfig
                    sed -i 's/127.0.0.1/172.17.0.1/g' ./jenkins-kubeconfig
                '''

                echo "Applying Kubernetes Manifests..."
                sh '''
                    export KUBECONFIG=./jenkins-kubeconfig
                    
                    # BYPASS TLS CHECK FOR LOCAL K3D
                    ./kubectl apply -f k8s/monitoring.yml --insecure-skip-tls-verify=true
                    
                    # If you have a separate file for your backend, you can also add:
                    # ./kubectl apply -f k8s/pvc.yml --insecure-skip-tls-verify=true
                    
                    ./kubectl rollout restart deployment backend --insecure-skip-tls-verify=true
                '''
            }
        }
    }
}
