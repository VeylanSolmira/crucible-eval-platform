monitoring
    test/inspect cloudwatch infrastructure
testing
    get all current tests integrated in run_tests.py to 100% -- about half fail
    bring tests to next level: assess what that precisely means, key unit tests for each component, key integration, percentage coverage, description of level after this
kubernetes migration
    explore putting each service on its own t2.micro -- cost implications (partially interested just from architectural experience)
security
    we haven't been doing so much with this recently because needing to get infrastructure up to higher levels of quality just for evaluation and testing. need to start circling back to this, e.g. the download v. evaluate distinction
    attack scenarios from 5-day-metr
infrastructure
    probably need to get a vpc/private subnets going for security considerations
documentation
    need to circle back: ensure every document in /docs is visible int he app, all the wiki features built out, slides need to be polished and inspected
interview prep
    revisit questions and work on schedule? differnet protocols to hone my knowledge of the platform
demos
    we sort of completed the first two from week-4-demo. need a comprehensive suite, even if not too expansive that we can run perhaps in an automated way

## docs
    ### 7-day-metr
        frontend evaluation history
            - [ ] Search and filter capabilities
        all of 8
        merge 10 with existing documentation task set
    ### week-3-metr
        1
            verify we have pre-submission syntax validation
            - Link errors to editor line numbers
            - Common error explanations
        2
            cpu and memory usage is present but have been broken for awhile, perhaps historical display would be nice/valuable
        3
            production test for rate limit
        4
            inspect of there's anythign left on the migration status
        5
            load to week-5-metr
        6
            security: automated scanning of all images?
        7
            all
        8
            all that's not already present
        9
            verify we still need or wants these (so include but with that note)
        12
             - Refactor global Redis clients to use app.state or dependency injection
        12
            all, but with note of evaluate how much we value this
        13
            all that's not already present
        14
            all
    ### week-4-demo
        1
            all
        2
            all, but there should be a demo section already
        3
            all
        4
            all
        5
            all
        6
            all
        7-10
            all