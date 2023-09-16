function toast(texte) {
    var wrapper = document.createElement('div')
    wrapper.className = "alert alert-success alert-dismissible fade show"
    wrapper.role = "alert"
    wrapper.textContent = texte
    var btn = document.createElement("button")
    btn.type = "button"
    btn.className = "btn-close"
    btn.setAttribute("data-bs-dismiss", "alert")
    btn.setAttribute("aria-label", "Close")
    wrapper.appendChild(btn)

    var alertPlaceholder = document.getElementById('liveAlertPlaceholder')
    alertPlaceholder.append(wrapper)

    setTimeout(function () { let alert = new bootstrap.Alert(wrapper); alert.close() }, 3500);
}

function updateTime() {
    var cDate = new Date()
    document.getElementById("dateTimeBlock").innerHTML = cDate.toLocaleTimeString()
}

function populateUsers(userdata) {
    let usersroot = document.getElementById("userbody")
    // Clear current users
    while (usersroot.firstChild) {
        usersroot.removeChild(usersroot.firstChild);
    }
    // Add new users
    userdata.forEach(element => {
        let row = usersroot.insertRow()
        let name = document.createElement("th")
        name.innerText = element["user"]
        name.setAttribute("scope", "row")
        row.appendChild(name)
        let timestamp = document.createElement("td")
        timestamp.innerText = new Date(element["start"]).toLocaleString()
        row.appendChild(timestamp)
    });
}

function handleResponse(json) {
    if (json["action"] === "update") {
        populateUsers(json["users"])
        toast(json["message"])
    } else if (json["action"] === "redirect") {
        window.location.replace("/")
    }
}

function updateUserData() {
    fetch("/active?" + new URLSearchParams({ event: event_code }))
        .then(data => data.json())
        .then(handleResponse)
}

const onScanSuccess = (decodedText) => {

    console.log(decodedText)

    let formData = new FormData();
    formData.append('user_code', decodedText);
    formData.append('event_code', event_code);

    fetch(`/scan`, { method: "POST", body: formData })
        .then((response) => {
            if (response.ok) {
                return response.json();
            } else {
                response.text().then(data => {
                    toast(data)
                });
            }
        })
        .then(handleResponse)
}

setInterval(updateUserData, 300000)
setInterval(updateTime, 1000)
updateUserData()

function initCamera() {
    let selectedDeviceId;
    const codeReader = new ZXing.BrowserQRCodeReader()
    console.log('ZXing code reader initialized')
    var reader = document.getElementById('reader')
    reader.children.namedItem("launchButton").remove()
    var video = document.createElement("video")
    video.style = "border: 1px solid gray"
    video.id = "video"
    reader.appendChild(video)

    codeReader.getVideoInputDevices()
      .then((videoInputDevices) => {
        selectedDeviceId = videoInputDevices[0].deviceId
        
        codeReader.decodeFromInputVideoDeviceContinuously(selectedDeviceId, 'video', (result, err) => {
            if (result) {
                // properly decoded qr code
                onScanSuccess(result)
            }
    
            if (err) {
                if (err instanceof ZXing.ChecksumException) {
                    console.log('A code was found, but its read value was not valid.')
                }
    
                if (err instanceof ZXing.FormatException) {
                    console.log('A code was found, but it was in a invalid format.')
                }
            }
        })
        
        console.log(`Started decode from camera with id ${selectedDeviceId}`)
      })
      .catch((err) => {
        console.error(err)
      })
}
