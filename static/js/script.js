// document.addEventListener('DOMContentLoaded', () => {
//     const startButton = document.getElementById('start');
//     const endButton = document.getElementById('end');
//     const cameraStream = document.getElementById('camera-stream');
    
//     let stream;

//     async function startCamera() {
//         try {
//             stream = await navigator.mediaDevices.getUserMedia({ video: true });
//             cameraStream.srcObject = stream;
//             cameraStream.style.display = 'block'; // Show the camera stream
//             startButton.style.display = 'none';
//             endButton.style.display = 'inline';
//         } catch (error) {
//             console.error('Error accessing camera:', error);
//         }
//     }

//     function stopCamera() {
//         if (stream) {
//             const tracks = stream.getTracks();
//             tracks.forEach(track => track.stop());
//             cameraStream.srcObject = null;
//             cameraStream.style.display = 'none'; // Hide the camera stream
//             startButton.style.display = 'inline';
//             endButton.style.display = 'none';
//         }
//     }

//     startButton.addEventListener('click', startCamera);
//     endButton.addEventListener('click', stopCamera);
// });


// document.addEventListener('DOMContentLoaded', () => {
//     const startButton = document.getElementById('start');
//     const endButton = document.getElementById('end');
//     const cameraStream = document.getElementById('camera-stream');
    
//     let stream;

//     // 카메라 시작 함수
//     async function startCamera() {
//         try {
//             // 비디오 해상도와 프레임 속도 설정
//             const constraints = {
//                 video: {
//                     facingMode: 'user',
//                     width: { ideal: 1280 },
//                     height: { ideal: 720 },
//                     frameRate: { ideal: 30 } // 프레임 속도 설정
//                 }
//             };

//             stream = await navigator.mediaDevices.getUserMedia(constraints);
//             cameraStream.srcObject = stream;
//             cameraStream.style.display = 'block'; // 카메라 스트림을 보여줍니다.
//             startButton.style.display = 'none'; // Start 버튼 숨기기
//             endButton.style.display = 'inline'; // End 버튼 보이기

//             // 비디오 스트림 상태 확인
//             cameraStream.addEventListener('loadedmetadata', () => {
//                 console.log('Video metadata loaded');
//             });

//             cameraStream.addEventListener('play', () => {
//                 console.log('Video is playing');
//             });

//             cameraStream.addEventListener('pause', () => {
//                 console.log('Video is paused');
//             });

//         } catch (error) {
//             console.error('Error accessing camera:', error);
//         }
//     }

//     // 카메라 종료 함수
//     function stopCamera() {
//         if (stream) {
//             const tracks = stream.getTracks();
//             tracks.forEach(track => track.stop());
//             cameraStream.srcObject = null;
//             cameraStream.style.display = 'none'; // 카메라 스트림 숨기기
//             startButton.style.display = 'inline'; // Start 버튼 보이기
//             endButton.style.display = 'none'; // End 버튼 숨기기
//         }
//     }

//     // Start 버튼 클릭 이벤트 리스너
//     startButton.addEventListener('click', startCamera);

//     // End 버튼 클릭 이벤트 리스너
//     endButton.addEventListener('click', stopCamera);

//     // 음성 합성 함수
//     function speak(text) {
//         const msg = new SpeechSynthesisUtterance(text);
//         window.speechSynthesis.speak(msg);
//     }

//     // 경고 메시지 가져오기
//     function fetchWarningMessage() {
//         fetch('/warning_message')
//             .then(response => response.json())
//             .then(data => {
//                 if (data.message) {
//                     speak(data.message);
//                 }
//             })
//             .catch(error => console.error('Error fetching warning message:', error));
//     }

//     // 주기적으로 경고 메시지 확인
//     setInterval(fetchWarningMessage, 1000); // 1초마다 호출
// });

document.addEventListener('DOMContentLoaded', () => {
    const startButton = document.getElementById('start');
    const endButton = document.getElementById('end');
    const cameraStream = document.getElementById('camera-stream');

    function showCameraStream() {
        cameraStream.style.display = 'block'; // 카메라 스트림 보이기
        startButton.style.display = 'none';
        endButton.style.display = 'inline';
    }

    function hideCameraStream() {
        cameraStream.style.display = 'none'; // 카메라 스트림 숨기기
        startButton.style.display = 'inline';
        endButton.style.display = 'none';
    }

    startButton.addEventListener('click', showCameraStream);
    endButton.addEventListener('click', hideCameraStream);
});



// 1초마다 감지된 객체 정보를 가져와서 업데이트
setInterval(() => {
    fetch('/get_top_objects')
        .then(response => response.json())
        .then(data => {
            document.getElementById('object1').innerText = data[0].label;
            document.getElementById('distance1').innerText = data[0].distance + 'm';
            document.getElementById('object2').innerText = data[1].label;
            document.getElementById('distance2').innerText = data[1].distance + 'm';
            document.getElementById('object3').innerText = data[2].label;
            document.getElementById('distance3').innerText = data[2].distance + 'm';
        })
        .catch(error => console.error('Error:', error));
}, 1000);  // 1초마다 업데이트