function toast(texte) {
    let elem = document.createElement("div");
    elem.className = "toast";
    elem.innerHTML = texte;
    document.body.appendChild(elem);
    setTimeout(function () { elem.remove() }, 3500);
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
        let item1 = document.createElement("td")
        item1.innerText = element[0]
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

    fetch(`/scan`, { method: "POST", body: formData})
        .then(data => data.json())
        .then(json => {
            toast(json['message'])
            populateUsers(json['users'])
        })
}

let html5QrcodeScanner = new Html5QrcodeScanner(
    "reader",
    {
        fps: 10,
        qrbox: 500,
        rememberLastUsedCamera: true
    },
      /* verbose= */ false);
html5QrcodeScanner.render(onScanSuccess);

setInterval(updateUserData, 300000)
updateUserData()
