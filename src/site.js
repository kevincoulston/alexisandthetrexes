// Count the T-Rexes: a little game from Count to Ten. Shows 1 to 10 dinosaurs in the yard; tap the matching number.
(function () {
  var game = document.getElementById('ar-count');
  if (!game) return;
  var yard = game.querySelector('.ar-yard');
  var say = game.querySelector('.ar-say');
  var pics = JSON.parse(yard.getAttribute('data-dinos'));
  // Spots in the yard (left %, bottom %), roughly back to front so nobody hides completely.
  var spots = [[6, 44], [24, 50], [44, 46], [64, 52], [82, 44], [2, 8], [20, 14], [40, 6], [60, 12], [78, 6]];
  var answer = 0;
  function round() {
    var n = answer;
    while (n === answer) n = 1 + Math.floor(Math.random() * 10);
    answer = n;
    yard.querySelectorAll('.ar-d').forEach(function (d) { d.remove(); });
    var order = spots.slice().sort(function () { return Math.random() - 0.5; }).slice(0, n);
    order.sort(function (a, b) { return b[1] - a[1]; });
    order.forEach(function (s, i) {
      var p = pics[Math.floor(Math.random() * pics.length)];
      var img = document.createElement('img');
      img.className = 'ar-d';
      img.src = p.src;
      img.alt = '';
      img.setAttribute('aria-hidden', 'true');
      img.width = p.w;
      img.height = p.h;
      img.style.left = s[0] + '%';
      img.style.bottom = s[1] + '%';
      if (Math.random() < 0.5) img.style.transform = 'scaleX(-1)';
      yard.appendChild(img);
    });
    yard.setAttribute('aria-label', 'A yard with some baby T-Rexes in it. How many can you count?');
    game.querySelectorAll('.ar-num').forEach(function (b) { b.classList.remove('ok', 'no'); });
  }
  game.querySelectorAll('.ar-num').forEach(function (b) {
    b.addEventListener('click', function () {
      var v = +b.textContent;
      if (v === answer) {
        b.classList.add('ok');
        say.textContent = 'Yes! ' + answer + (answer === 1 ? ' T-Rex!' : ' T-Rexes!') + ' Here comes a new yard...';
        setTimeout(round, 1600);
      } else {
        b.classList.add('no');
        say.textContent = 'Not quite. Count them again, pointing at each one.';
      }
    });
  });
  round();
})();
