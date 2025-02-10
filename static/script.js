const signUpButton = document.getElementById('signUp');
const signInButton = document.getElementById('signIn');
const container = document.getElementById('container');

signUpButton.addEventListener('click', () => {
	container.classList.add("right-panel-active");
});

signInButton.addEventListener('click', () => {
	container.classList.remove("right-panel-active");
});

function sUp(x) {
  container.classList.add("right-panel-active");
}

function sIn(x) {
  container.classList.remove("right-panel-active");
}

function updateUserTypeLabel(value) {
  const userTypeLabel = document.getElementById('userTypeLabel');
  userTypeLabel.textContent = value == 0 ? 'User' : 'Admin';
}