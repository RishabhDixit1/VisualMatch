VisualMatch: Image Recognition and Suggestion System
VisualMatch is a full-stack web application that analyzes user-uploaded images to identify objects and provides dynamic suggestions for improving the image or its environment. The entire project is containerized with Docker for easy, "plug-and-play" setup.
![alt text](<Screenshot (1481).png>)
Tech Stack
Frontend: React
Backend: Python, Flask
Database: PostgreSQL
AI / ML: PyTorch, Hugging Face Transformers
Containerization: Docker, Docker Compose
How to Run This Project
You only need Docker and Git installed on your machine.
Clone the repository: https://github.com/RishabhDixit1/VisualMatch.git
Use code with caution.
Sh
Navigate into the project directory:
cd VisualMatch
Use code with caution.
Sh
Build and run the containers:
This single command starts the frontend, backend, and database.
docker-compose up --build
Use code with caution.
Sh
Note: The first launch will take several minutes to download the ML model and build the images. Subsequent launches will be much faster.
Access the application:
Open your web browser and go to:
http://localhost
How to Use the App
Click "Choose File" to select an image from your computer.
Click the "Analyze Image" button.
Wait for the analysis to complete.
View the detected objects and improvement suggestions on the right-hand side.
To Stop the Application
Press Ctrl + C in the terminal where the application is running.
Run the following command to remove the containers and network:
docker-compose down

