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
        name.innerText = element["person"]
        name.setAttribute("scope", "row")
        row.appendChild(name)
        let timestamp = document.createElement("td")
        timestamp.innerText = new Date(element["start"]).toLocaleString()
        row.appendChild(timestamp)
    });
}

function handleResponse(json) {
    if(json["action"] === "update") {
        populateUsers(json["users"])
        toast(json["message"])
    } else if(json["action"] === "redirect") {
        window.location.replace("/")
    }
}

function updateUserData() {
    fetch("/active?" + new URLSearchParams({ event: event_code }))
        .then(data => data.json())
        .then(handleResponse)
}

function onScanSuccess(decodedText, decodedResult) {
    if (html5QrcodeScanner.getState() !== Html5QrcodeScannerState.NOT_STARTED) {
        html5QrcodeScanner.pause();
        setTimeout(function () { html5QrcodeScanner.resume() }, 2000);
    }

    let formData = new FormData();
    formData.append('name', decodedText);
    formData.append('event', event_code);

    fetch(`/scan`, { method: "POST", body: formData })
        .then((response) => {
            if (response.ok) {
                return response.json();
            } else {
                throw Error("Not a valid QR code");
            }
        })
        .then(handleResponse).catch(data => {
            toast(data)
        })
}

let html5QrcodeScanner = new Html5QrcodeScanner(
    "reader",
    {
        fps: 10,
        rememberLastUsedCamera: true
    },
      /* verbose= */ false);
html5QrcodeScanner.render(onScanSuccess);

setInterval(updateUserData, 300000)
updateUserData()
