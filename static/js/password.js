// პაროლის ჩვენება / დამალვა — ყველა პაროლის ველს ემატება „თვალის“ ღილაკი
document.querySelectorAll('input[type="password"]').forEach(function (input) {
  const wrapper = document.createElement('div');
  wrapper.className = 'password-field';
  input.parentNode.insertBefore(wrapper, input);
  wrapper.appendChild(input);

  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'password-toggle';
  button.setAttribute('aria-label', 'პაროლის ჩვენება');
  button.textContent = '👁';
  wrapper.appendChild(button);

  button.addEventListener('click', function () {
    const hidden = input.type === 'password';
    input.type = hidden ? 'text' : 'password';
    button.textContent = hidden ? '🙈' : '👁';
    button.setAttribute('aria-label', hidden ? 'პაროლის დამალვა' : 'პაროლის ჩვენება');
    input.focus();
  });
});
