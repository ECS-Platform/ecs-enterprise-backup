// ECS demo: make Jenkins auth deterministic on every boot.
// Creates an admin account (idempotent) and allows anonymous READ so the ECS
// Jenkins connector reports connected=true, while writes (create job / build)
// require the admin credentials used by demo-data/seed_jenkins_demo.sh.
import jenkins.model.Jenkins
import hudson.model.User
import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.HudsonPrivateSecurityRealm.Details
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy

def instance = Jenkins.get()

String user = System.getenv('JENKINS_ADMIN_USER') ?: 'admin'
String pass = System.getenv('JENKINS_ADMIN_PASSWORD') ?: 'admin123'

def realm = (instance.getSecurityRealm() instanceof HudsonPrivateSecurityRealm) \
    ? instance.getSecurityRealm() : new HudsonPrivateSecurityRealm(false)
instance.setSecurityRealm(realm)

// Force the admin password deterministically (idempotent across reboots and
// persisted volumes): create the account if missing, otherwise reset its password.
def existing = realm.getAllUsers().find { it.id == user }
if (existing == null) {
    realm.createAccount(user, pass)
} else {
    existing.addProperty(Details.fromPlainPassword(pass))
}

def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(true)   // ECS connector can read without credentials
instance.setAuthorizationStrategy(strategy)

instance.save()
