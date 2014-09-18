import serpent
from pyethereum import transactions, blocks, processblock, utils
import ipdb

class NonceSingleton(object):
    nonces = {}

    @classmethod
    def inc(cls, user):
        nonce = -1
        try:
            nonce = cls.nonces[user]
        except KeyError:
            cls.nonces[user] = 0
            nonce = cls.nonces[user]

        cls.nonces[user] += 1

        return nonce

class EthereumUser(object):
    START_BALANCE = 10 ** 18

    def __init__(self, name, genesis=None):
        self.private_key = utils.sha3(name)
        self.addr = utils.privtoaddr(self.private_key)
        self.genesis = genesis or blocks.genesis({self.addr: self.START_BALANCE})

    def apply_tx(self, tx):
        return processblock.apply_tx(self.genesis, tx)

class Message(object):
    DEFAULT_GASPRICE = 0
    DEFAULT_STARTGAS = 10 ** 4

    def __init__(self, to, donate_to, value=0):
        self.to = to
        self.value = value
        self.donate_to = donate_to
        self.data = serpent.encode_datalist([self._data_code(),
                                             donate_to])
        self.tx = lambda user: transactions.Transaction(NonceSingleton.inc(user),
                                                        self.DEFAULT_GASPRICE,
                                                        self.DEFAULT_STARTGAS,
                                                        to,
                                                        value,
                                                        self.data)

    def _data_code(self):
        raise NotImplementedError()

    def execute(self, from_):
        signed_tx = self.tx(from_).sign(from_.private_key)
        return processblock.apply_transaction(from_.genesis, signed_tx)

class Campaign(Message):
    def _data_code(self):
        return 0

class Donation(Message):
    def _data_code(self):
        return 1

class Report(Message):
    def _data_code(self):
        return 2

class Crowdfund(object):
    def __init__(self, root_user):
        self.user = root_user
        self.code = serpent.compile(open('./crowdfund.se').read())
        tx = transactions.contract(NonceSingleton.inc(root_user),
                                   Message.DEFAULT_GASPRICE,
                                   Message.DEFAULT_STARTGAS,
                                   0,
                                   self.code).sign(root_user.private_key)

        print "Made crowdfund tx: {}".format(tx)

        self.contract = self._wrap_contract_response(
            processblock.apply_transaction(root_user.genesis, tx))



    def _wrap_contract_response(self, response):
        ans, result = response
        print "Successful? {}. Made: {}".format(ans, result)

        return result

    def campaign(self, donate_to, from_):
        campaign = Campaign(self.contract, donate_to)
        print "Made campaign: {}".format(campaign)

        return self._wrap_contract_response(campaign.execute(from_))

    def donation(self, donate_to, from_, value):
        donation = Donation(self.contract, donate_to, value)

        print "Made donation: {}".format(donation)

        return self._wrap_contract_response(donation.execute(from_))

    def report(self, donate_to, from_):
        report = Report(self.contract, donate_to)

        print "Made report: {}".format(report)

        return self._wrap_contract_response(report.execute(from_))

def frombytes(b):
    return 0 if len(b) == 0 else ord(b[-1]) + 256 * frombytes(b[:-1])

def print_report(report):
    # ipdb.set_trace()
    print "Decoded: {}".format(frombytes(report))

def main():
    root = EthereumUser("helloworld")
    alice = EthereumUser("alice", genesis=root.genesis)
    bob = EthereumUser("bob", genesis=root.genesis)

    fund = Crowdfund(root)

    campaign = fund.campaign(100, alice)
    print_report(fund.report(campaign, alice))
    print_report(fund.report(campaign, bob))
    fund.donation(campaign, root, 50)
    print_report(fund.report(campaign, bob))

    fund.donation(campaign, root, 100)

    print_report(fund.report(campaign, bob))

if __name__ == '__main__':
    main()
