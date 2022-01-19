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
        let row = document.createElement("tr")
        let item1 = document.createElement("th")
        item1.innerText = element[0]
        item1.setAttribute("scope", "row")
        row.appendChild(item1)
        let item2 = document.createElement("td")
        item2.innerText = element[1]
        row.appendChild(item2)
        usersroot.appendChild(row)
    });
}

function updateUserData() {
    const event = "training"
    fetch(`/users/${event}`)
        .then(data => data.json())
        .then(json => {
            populateUsers(json)
            toast("Updated User Data")
        })
}

function onScanSuccess(decodedText, decodedResult) {
    if (html5QrcodeScanner.getState() !== Html5QrcodeScannerState.NOT_STARTED) {
        html5QrcodeScanner.pause();
        setTimeout(function () { html5QrcodeScanner.resume() }, 2000);
    }
    const event = "training"

    let formData = new FormData();
    formData.append('name', decodedText);
    formData.append('event', event);

    fetch(`/scan`, { method: "POST", body: formData })
        .then((response) => {
            if (response.ok) {
                return response.json();
            } else {
                throw Error("Not a valid QR code");
            }
        })
        .then(json => {
            toast(json['message'])
            populateUsers(json['users'])
        }).catch(data => {
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
