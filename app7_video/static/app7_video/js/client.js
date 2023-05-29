
'use strict';

/* globals MediaRecorder */

let mediaRecorder;
let recordedBlobs;

var instructions = new bootstrap.Modal(document.getElementById('modalinstructionsvideo'), {backdrop:"static", keyboard:false});
var instructions2 = new bootstrap.Modal(document.getElementById('modalinstructionsvideo2'), {backdrop:"static", keyboard:false});
var instructions3 = new bootstrap.Modal(document.getElementById('modalinstructionsvideo3'), {backdrop:"static", keyboard:false});

instructions.show();

var recordspin = document.getElementById("recording");
var waitspin = document.getElementById("spinner");
var recordmsg = document.getElementById("record-msg");
var finishmsg = document.getElementById("finish-msg");
var waitmsg = document.getElementById("wait-msg");
var next1 = document.getElementById("next");
var next2 = document.getElementById("next2");


const recordButton = document.querySelector('button#record');
recordButton.addEventListener('click', () => {
    instructions3.hide();
    recordmsg.style.display = 'block';
    recordspin.style.display = 'block';
    const gumVideo = document.querySelector('video#gum');
    gumVideo.hidden = false;
    startRecording();
    StopthenSend();
});

next1.addEventListener('click', () => {
    instructions.hide();
    instructions2.show();
});

next2.addEventListener('click', () => {
    instructions2.hide();
    instructions3.show();
});


function handleDataAvailable(event) {
//  console.log('handleDataAvailable', event);
  if (event.data && event.data.size > 0) {
    recordedBlobs.push(event.data);
  }
}


function getSupportedMimeTypes() {
  const possibleTypes = [
    'video/webm',
    'video/mp4'
  ];
  return possibleTypes.filter(mimeType => {
    return MediaRecorder.isTypeSupported(mimeType);
  });
}


async function startRecording() {
  recordedBlobs = [];
  const mimeType = await getSupportedMimeTypes()[0];
  const options = {mimeType};
  try {
    mediaRecorder = await new MediaRecorder(window.stream, options);
  } catch (e) {
    console.error('Exception while creating MediaRecorder:', e);
    return;
  }
//  console.log('Created MediaRecorder', mediaRecorder, 'with options', options);
  mediaRecorder.ondataavailable = handleDataAvailable;
  mediaRecorder.start();
//  console.log('MediaRecorder started', mediaRecorder);
}


const delay = ms => new Promise(res => setTimeout(res, ms));


async function StopthenSend(){
    await delay(20000);
    await mediaRecorder.stop();
    recordmsg.style.display = 'none';
    recordspin.style.display = 'none';
    waitspin.style.display = 'block';
    waitmsg.style.display = 'block';
    await delay(500);
    await sendVideo();
}


function handleSuccess(stream) {
  recordButton.disabled = false;
//  console.log('getUserMedia() got stream:', stream);
  window.stream = stream;
  const gumVideo = document.querySelector('video#gum');
  gumVideo.srcObject = stream;
  const gumVideo2 = document.querySelector('video#gum2');
  gumVideo2.srcObject = stream;
}


async function init(constraints) {
  try {
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    handleSuccess(stream);
  } catch (e) {
    console.error('navigator.getUserMedia error:', e);
  }
}


document.querySelector('button#start').addEventListener('click', async () => {
  document.querySelector('button#start').disabled = true;
  document.querySelector('button#next').disabled = false;
  const constraints = {
    video: {
      width: 1280, height: 720, facingMode: 'user',
    }
  };
  await init(constraints);
});

let flipBtn = document.querySelector('#flip-btn');
let shouldFaceUser = true;

async function enumVideoDevices(){
    let result = 0;
    await navigator.mediaDevices.enumerateDevices().then(function (devices) {
        devices.forEach(function(device){
            if (device.kind == 'videoinput'){
                result++;
            };
        });
    });
    if (result > 1){
        flipBtn.hidden = false;
    };
};

enumVideoDevices();

flipBtn.addEventListener('click', function(){
  if( window.stream == null ) return
  // we need to flip, stop everything
  window.stream.getTracks().forEach(t => {
    t.stop();
  });
  // toggle / flip
  shouldFaceUser = !shouldFaceUser;
  const constraints = {
    video: {
        width: 1280, height: 720,
    }
  }
  if(shouldFaceUser){
    constraints.video.facingMode = 'user';
  } else {
    constraints.video.facingMode = 'environment';
  };
  init(constraints)
})


async function sendVideo(){
    var blob = await new Blob(recordedBlobs, {type: 'video/webm'});
    function getBase64(file, onLoadCallback) {
        return new Promise(function(resolve, reject) {
        var reader = new FileReader();
        reader.onload = function() { resolve(reader.result ); };
        reader.onerror = reject;
        reader.readAsDataURL(file);
        });
        }

        var promise = getBase64(blob);
        console.log('promise:', promise)
        promise.then(function(result) {
            var formData = new FormData();
            var b64_vdo = result.replace("data:video/webm;base64,", "");
            formData.append('filename', document.getElementById('folder').value);
            formData.append('vdo_rec', b64_vdo);
            fetch('/recognize/true/', {
        method: 'POST',
        body: formData
        })
    .then(response => {
        waitspin.style.animationPlayState='';
        waitmsg.style.display = 'none';
        finishmsg.style.display = 'block';
        waitspin.classList.remove("text-warning");
        waitspin.classList.add("text-success");
        setTimeout(() => {
            location.href="/";
        }, 3000);
        })
    .catch(error => {
        console.log(error.name);
        });
    });
        };

