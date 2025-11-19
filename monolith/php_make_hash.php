
<?php
// php_make_hash.php - prints a bcrypt hash for a given password
// Usage: php php_make_hash.php yourpassword
if ($argc < 2) {
    fwrite(STDERR, "Usage: php php_make_hash.php <password>\n");
    exit(1);
}
$pwd = $argv[1];
$hash = password_hash($pwd, PASSWORD_BCRYPT);
echo $hash . PHP_EOL;
